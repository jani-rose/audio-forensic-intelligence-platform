from django.db import models


class AudioFile(models.Model):
    case_id = models.CharField(max_length=50)
    filename = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to='audio/')

    duration = models.FloatField(null=True, blank=True)
    sample_rate = models.IntegerField(null=True, blank=True)

    fingerprint = models.TextField(null=True, blank=True)
    mfcc_features = models.TextField(null=True, blank=True)
    watermark = models.CharField(max_length=100, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename

    def duration_display(self):
        """Return duration as MM:SS string."""
        if self.duration is None:
            return "N/A"
        mins = int(self.duration // 60)
        secs = self.duration % 60
        return f"{mins:02d}:{secs:05.2f}"


class VerificationRecord(models.Model):
    original_audio = models.ForeignKey(
        AudioFile,
        on_delete=models.CASCADE,
        related_name='original_records',
    )
    suspect_audio = models.ForeignKey(
        AudioFile,
        on_delete=models.CASCADE,
        related_name='suspect_records',
    )
    similarity_score = models.FloatField(default=0)
    tamper_status = models.CharField(max_length=50, default="Unknown")
    tampered_segment = models.CharField(max_length=100, null=True, blank=True)
    result = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate comparison records for the same pair
        unique_together = ('original_audio', 'suspect_audio')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_audio} vs {self.suspect_audio}"
