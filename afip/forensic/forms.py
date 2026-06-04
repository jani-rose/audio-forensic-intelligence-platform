import os
from django import forms
from .models import AudioFile

ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}


class AudioFileForm(forms.ModelForm):

    class Meta:
        model = AudioFile
        fields = ['case_id', 'filename', 'audio_file']
        widgets = {
            'case_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. CASE001',
            }),
            'filename': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descriptive name for this evidence',
            }),
            'audio_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.mp3,.wav,.ogg,.flac,.aac,.m4a',
            }),
        }
        labels = {
            'case_id': 'Case ID',
            'filename': 'Evidence Label',
            'audio_file': 'Audio File',
        }

    def clean_audio_file(self):
        f = self.cleaned_data.get('audio_file')
        if f:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f"Unsupported file type '{ext}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )
        return f
