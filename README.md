# Audio Forensic Intelligence Platform (AFIP)

## Overview

The Audio Forensic Intelligence Platform (AFIP) is a web-based forensic analysis system developed using Django, Python, Librosa, Bootstrap, and SQLite.

The platform enables users to upload audio recordings, extract forensic metadata, generate audio fingerprints, perform similarity analysis, verify authenticity, validate forensic watermarks, identify potentially modified recordings, and generate PDF forensic reports.

AFIP demonstrates the application of digital signal processing and audio forensic techniques in a centralized investigation platform.

---

## Features

### Audio Evidence Management

* Audio file upload
* Audio storage and management
* Case ID tracking
* Evidence listing

### Metadata Extraction

Automatic extraction of:

* Audio duration
* Sample rate

### MFCC Feature Extraction

The platform extracts Mel Frequency Cepstral Coefficients (MFCCs) from uploaded audio files for forensic analysis.

### Audio Fingerprinting

* MFCC-based fingerprint generation
* SHA256 fingerprint creation
* Fingerprint storage

### Similarity Analysis

* Audio comparison using extracted MFCC features
* Similarity score generation
* Verification result generation

### Authenticity Verification

Verification results are classified as:

* Authentic
* Likely Authentic
* Potentially Modified

### Watermark Generation and Validation

* Automatic forensic watermark generation
* Watermark validation
* Evidence integrity verification

### Tamper Detection

* Potential tampering identification
* Estimated tampered segment indication

### Forensic Reporting

Automatic PDF report generation containing:

* Case information
* Audio metadata
* Fingerprint information
* Watermark status
* Similarity analysis
* Tamper detection results

### Dashboard Analytics

* Total audio count
* Verification statistics
* Authentic recordings count
* Tampered recordings count
* Verification history

---

## Technology Stack

### Backend

* Python
* Django

### Audio Processing

* Librosa
* NumPy

### Database

* SQLite

### Frontend

* HTML
* CSS
* Bootstrap 5

### Reporting

* ReportLab

---

## System Workflow

Audio Upload

↓

Metadata Extraction

↓

MFCC Feature Extraction

↓

Fingerprint Generation

↓

Watermark Generation

↓

Similarity Analysis

↓

Authenticity Verification

↓

Tamper Detection

↓

PDF Report Generation

---

## Project Structure

```text
Audio_Forensic_Intelligence_Platform
│
├── afip
│   ├── forensic
│   ├── media
│   ├── manage.py
│   └── db.sqlite3
│
├── Audio Samples
│
├── Project_Documents
│
└── README.md
```

---

## Current Capabilities

* Audio Upload
* Audio Storage
* Metadata Extraction
* MFCC Feature Extraction
* MFCC-Based Audio Fingerprinting
* Similarity Analysis
* Authenticity Verification
* Watermark Generation and Validation
* Tamper Detection
* Dashboard Analytics
* PDF Forensic Report Generation

---

## Future Enhancements

* Real Tamper Localization
* Audio Watermark Embedding
* Deepfake Audio Detection
* Speaker Identification
* Chain of Custody Management
* Case Management System
* AI-Based Audio Forensics
* Cloud Deployment

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
```

### Navigate to Project

```bash
cd Audio_Forensic_Intelligence_Platform/afip
```

### Create Virtual Environment

```bash
python -m venv env
```

### Activate Environment

Windows:

```bash
env\Scripts\activate
```

### Install Dependencies

```bash
pip install django librosa numpy reportlab
```

### Run Migrations

```bash
python manage.py migrate
```

### Start Server

```bash
python manage.py runserver
```

### Open Application

```text
http://127.0.0.1:8000
```

---

## Author

Author

Jani Rose Lawwellman

Audio Forensic Intelligence Platform developed using Django, Python, Librosa, NumPy, Bootstrap, SQLite, and ReportLab.