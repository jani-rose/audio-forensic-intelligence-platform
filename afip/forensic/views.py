import math
import hashlib
import numpy as np

from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import librosa

from .models import AudioFile, VerificationRecord
from .forms import AudioFileForm


# ─── Watermark ────────────────────────────────────────────────────────────────

def verify_watermark(audio):
    expected = f"AFIP_{audio.case_id}"
    return "Valid" if audio.watermark == expected else "Invalid"


# ─── Fingerprint comparison (character-level SHA256 match) ────────────────────

def compare_fingerprints(fp1, fp2):
    if not fp1 or not fp2:
        return 0.0, "Invalid Comparison"
    if fp1 == fp2:
        return 100.0, "Authentic"
    matches = sum(a == b for a, b in zip(fp1, fp2))
    similarity = (matches / len(fp1)) * 100
    result = "Likely Authentic" if similarity >= 90 else "Potentially Modified"
    return similarity, result


# ─── MFCC cosine similarity (replaces unreliable Euclidean formula) ───────────

def compare_mfcc_features(mfcc1_str, mfcc2_str):
    if not mfcc1_str or not mfcc2_str:
        return 0.0, "Invalid Comparison"

    try:
        v1 = np.array([float(x) for x in mfcc1_str.split(',')])
        v2 = np.array([float(x) for x in mfcc2_str.split(',')])

        # Cosine similarity: dot(v1,v2) / (||v1|| * ||v2||)
        dot = np.dot(v1, v2)
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)

        if norm == 0:
            return 0.0, "Invalid Comparison"

        cosine_sim = dot / norm                  # range -1 to 1
        similarity = (cosine_sim + 1) / 2 * 100  # scale to 0–100

        if similarity >= 80:
            result = "Authentic"
        elif similarity >= 50:
            result = "Likely Authentic"
        else:
            result = "Potentially Modified"

        return float(similarity), result

    except (ValueError, ZeroDivisionError):
        return 0.0, "Invalid Comparison"


# ─── Allowed audio MIME types ─────────────────────────────────────────────────

ALLOWED_AUDIO_TYPES = {
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav',
    'audio/ogg', 'audio/flac', 'audio/aac', 'audio/mp4',
    'audio/x-m4a', 'video/mp4',  # some browsers send mp4 for .m4a
}

ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}


def is_valid_audio_file(uploaded_file):
    import os
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ─── Home view ────────────────────────────────────────────────────────────────

def home(request):
    if request.method == 'POST':
        form = AudioFileForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES.get('audio_file')

            # File type validation
            if not is_valid_audio_file(uploaded_file):
                messages.error(
                    request,
                    "Invalid file type. Please upload an audio file "
                    "(.mp3, .wav, .ogg, .flac, .aac, .m4a)."
                )
                return redirect('/')

            try:
                audio = form.save()

                # Load and analyse audio
                y, sr = librosa.load(audio.audio_file.path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)

                audio.duration = round(duration, 3)
                audio.sample_rate = int(sr)

                # MFCC extraction
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                mfcc_mean = mfcc.mean(axis=1)
                audio.mfcc_features = ",".join(
                    [str(float(v)) for v in mfcc_mean]
                )

                # SHA-256 fingerprint
                fingerprint_data = "_".join(
                    [f"{v:.4f}" for v in mfcc_mean]
                )
                audio.fingerprint = hashlib.sha256(
                    fingerprint_data.encode()
                ).hexdigest()

                # Watermark
                audio.watermark = f"AFIP_{audio.case_id}"

                audio.save()

                # Compare against all existing files
                existing_files = AudioFile.objects.exclude(id=audio.id)
                for existing in existing_files:
                    if not existing.mfcc_features:
                        continue

                    similarity, result = compare_mfcc_features(
                        audio.mfcc_features,
                        existing.mfcc_features
                    )

                    if similarity < 80:
                        tamper_status = "Potential Tampering"
                        # Full frame-by-frame MFCC localization
                        # Load both files and compute per-frame MFCC difference
                        try:
                            y2, sr2 = librosa.load(existing.audio_file.path, sr=None)
                            hop_length = 512

                            # Compute full MFCC matrices (frames x 13)
                            mfcc_new = librosa.feature.mfcc(y=y,  sr=sr,  n_mfcc=13, hop_length=hop_length)
                            mfcc_old = librosa.feature.mfcc(y=y2, sr=sr2, n_mfcc=13, hop_length=hop_length)

                            # Align lengths (trim to shorter)
                            min_frames = min(mfcc_new.shape[1], mfcc_old.shape[1])
                            mfcc_new = mfcc_new[:, :min_frames]
                            mfcc_old = mfcc_old[:, :min_frames]

                            # Per-frame L2 distance
                            frame_diffs = np.linalg.norm(mfcc_new - mfcc_old, axis=0)

                            # Find the frame with maximum divergence
                            peak_frame = int(np.argmax(frame_diffs))

                            # Find the contiguous region above 70th percentile around the peak
                            threshold = np.percentile(frame_diffs, 70)
                            above = frame_diffs > threshold

                            # Walk left and right from peak to find the suspicious region
                            start_frame = peak_frame
                            end_frame   = peak_frame
                            while start_frame > 0 and above[start_frame - 1]:
                                start_frame -= 1
                            while end_frame < min_frames - 1 and above[end_frame + 1]:
                                end_frame += 1

                            # Convert frames → seconds
                            def frames_to_ts(f):
                                secs = (f * hop_length) / sr
                                m = int(secs // 60)
                                s = secs % 60
                                return f"{m:02d}:{s:05.2f}"

                            tampered_segment = (
                                f"{frames_to_ts(start_frame)} – {frames_to_ts(end_frame)}"
                            )

                        except Exception:
                            tampered_segment = "Undetermined"
                    else:
                        tamper_status = "No Tampering"
                        tampered_segment = "None"

                    # Update existing record OR create new one
                    # (update_or_create ensures re-uploads always get fresh results)
                    VerificationRecord.objects.update_or_create(
                        original_audio=existing,
                        suspect_audio=audio,
                        defaults={
                            'similarity_score': similarity,
                            'result': result,
                            'tamper_status': tamper_status,
                            'tampered_segment': tampered_segment,
                        }
                    )

                messages.success(
                    request,
                    f"Audio '{audio.filename}' uploaded and analysed successfully."
                )

            except Exception as e:
                # Clean up partially-saved record if it exists
                try:
                    audio.delete()
                except Exception:
                    pass
                messages.error(
                    request,
                    f"Failed to process audio file: {str(e)}. "
                    "Please ensure the file is a valid audio file."
                )

            return redirect('/')

    else:
        form = AudioFileForm()

    audio_files = AudioFile.objects.all().order_by('-uploaded_at')
    verification_records = VerificationRecord.objects.all().order_by('-id')

    total_audio = AudioFile.objects.count()
    total_verifications = VerificationRecord.objects.count()
    total_authentic = VerificationRecord.objects.filter(result="Authentic").count()
    total_tampered = VerificationRecord.objects.filter(
        tamper_status="Potential Tampering"
    ).count()

    return render(request, 'home.html', {
        'form': form,
        'audio_files': audio_files,
        'verification_records': verification_records,
        'total_audio': total_audio,
        'total_verifications': total_verifications,
        'total_authentic': total_authentic,
        'total_tampered': total_tampered,
    })


# ─── Delete audio view ────────────────────────────────────────────────────────

def delete_audio(request, audio_id):
    audio = get_object_or_404(AudioFile, id=audio_id)
    if request.method == 'POST':
        filename = audio.filename
        # Delete the physical file
        try:
            import os
            if audio.audio_file and os.path.isfile(audio.audio_file.path):
                os.remove(audio.audio_file.path)
        except Exception:
            pass
        audio.delete()
        messages.success(request, f"'{filename}' deleted successfully.")
    return redirect('/')


# ─── PDF Forensic Report ──────────────────────────────────────────────────────

def generate_report(request, audio_id):
    audio = get_object_or_404(AudioFile, id=audio_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename=forensic_report_{audio.case_id}.pdf'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ForensicTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=14,
        spaceAfter=6,
        borderPad=4,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        leading=14,
    )

    watermark_status = verify_watermark(audio)

    # Latest verification record for this file
    verification = (
        VerificationRecord.objects
        .filter(suspect_audio=audio)
        .order_by('-id')
        .first()
    )

    elements = []

    # ── Header ──
    elements.append(Paragraph("Audio Forensic Intelligence Platform", title_style))
    elements.append(Paragraph(
        f"Forensic Evidence Report  |  Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        subtitle_style
    ))

    # Divider
    elements.append(Table(
        [['']],
        colWidths=[17 * cm],
        style=TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.HexColor('#1e40af')),
        ])
    ))
    elements.append(Spacer(1, 12))

    # ── Evidence Details ──
    elements.append(Paragraph("Evidence Details", section_style))
    evidence_data = [
        ['Field', 'Value'],
        ['Case ID', audio.case_id],
        ['Filename', audio.filename],
        ['Duration', f"{audio.duration:.3f} seconds" if audio.duration else "N/A"],
        ['Sample Rate', f"{audio.sample_rate} Hz" if audio.sample_rate else "N/A"],
        ['Upload Timestamp', audio.uploaded_at.strftime('%Y-%m-%d %H:%M:%S UTC')],
    ]
    evidence_table = Table(evidence_data, colWidths=[5 * cm, 12 * cm])
    evidence_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(evidence_table)
    elements.append(Spacer(1, 10))

    # ── Watermark & Integrity ──
    elements.append(Paragraph("Watermark & Integrity", section_style))
    wm_color = colors.HexColor('#16a34a') if watermark_status == "Valid" else colors.HexColor('#dc2626')
    integrity_data = [
        ['Field', 'Value'],
        ['Watermark', audio.watermark or 'N/A'],
        ['Watermark Status', watermark_status],
        ['SHA-256 Fingerprint', audio.fingerprint or 'N/A'],
    ]
    integrity_table = Table(integrity_data, colWidths=[5 * cm, 12 * cm])
    integrity_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (1, 2), (1, 2), wm_color),
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (1, 3), (1, 3), True),
    ]))
    elements.append(integrity_table)
    elements.append(Spacer(1, 10))

    # ── Verification Results ──
    elements.append(Paragraph("Verification & Tamper Analysis", section_style))

    if verification:
        result_color = {
            "Authentic": colors.HexColor('#16a34a'),
            "Likely Authentic": colors.HexColor('#d97706'),
        }.get(verification.result, colors.HexColor('#dc2626'))

        tamper_color = (
            colors.HexColor('#16a34a')
            if verification.tamper_status == "No Tampering"
            else colors.HexColor('#dc2626')
        )

        verification_data = [
            ['Field', 'Value'],
            ['Compared Against', str(verification.original_audio)],
            ['Similarity Score', f"{verification.similarity_score:.2f}%"],
            ['Authenticity Result', verification.result],
            ['Tamper Status', verification.tamper_status],
            ['Tampered Segment', verification.tampered_segment or 'N/A'],
        ]
        v_table = Table(verification_data, colWidths=[5 * cm, 12 * cm])
        v_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (1, 3), (1, 3), result_color),
            ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1, 4), (1, 4), tamper_color),
            ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(v_table)
    else:
        elements.append(Paragraph(
            "No verification record found. This file has not been compared against any existing evidence.",
            body_style
        ))

    elements.append(Spacer(1, 20))

    # ── Footer ──
    elements.append(Table(
        [['']],
        colWidths=[17 * cm],
        style=TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#94a3b8')),
        ])
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "This report was generated automatically by the Audio Forensic Intelligence Platform. "
        "Results are based on MFCC cosine similarity analysis and SHA-256 fingerprinting. "
        "This document should be reviewed by a qualified forensic examiner before use in legal proceedings.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.HexColor('#94a3b8'), leading=10)
    ))

    doc.build(elements)
    return response
