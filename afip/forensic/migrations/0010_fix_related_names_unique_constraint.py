from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('forensic', '0009_verificationrecord_tampered_segment'),
    ]

    operations = [
        # Fix related_name clash from old model
        migrations.AlterField(
            model_name='verificationrecord',
            name='original_audio',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='original_records',
                to='forensic.audiofile',
            ),
        ),
        migrations.AlterField(
            model_name='verificationrecord',
            name='suspect_audio',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='suspect_records',
                to='forensic.audiofile',
            ),
        ),
        # Add unique constraint to prevent duplicate comparison pairs
        migrations.AlterUniqueTogether(
            name='verificationrecord',
            unique_together={('original_audio', 'suspect_audio')},
        ),
    ]
