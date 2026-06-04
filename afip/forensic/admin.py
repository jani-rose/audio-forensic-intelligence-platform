from django.contrib import admin
from .models import AudioFile, VerificationRecord


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = ('case_id', 'filename', 'duration', 'sample_rate', 'watermark', 'uploaded_at')
    search_fields = ('case_id', 'filename')
    list_filter = ('uploaded_at',)
    readonly_fields = ('fingerprint', 'mfcc_features', 'watermark', 'duration', 'sample_rate', 'uploaded_at')
    ordering = ('-uploaded_at',)


@admin.register(VerificationRecord)
class VerificationRecordAdmin(admin.ModelAdmin):
    list_display = ('original_audio', 'suspect_audio', 'similarity_score', 'result', 'tamper_status', 'created_at')
    search_fields = ('original_audio__filename', 'suspect_audio__filename')
    list_filter = ('result', 'tamper_status', 'created_at')
    readonly_fields = ('similarity_score', 'result', 'tamper_status', 'tampered_segment', 'created_at')
    ordering = ('-created_at',)
