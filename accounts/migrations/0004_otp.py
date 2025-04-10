# Generated by Django 5.2 on 2025-04-10 09:16

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_profile_picture_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='OTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='email address')),
                ('code', models.CharField(max_length=6, verbose_name='OTP code')),
                ('action', models.CharField(choices=[('REGISTRATION', 'Registration'), ('BOOKING', 'Booking'), ('PASSWORD_RESET', 'Password Reset'), ('EMAIL_CHANGE', 'Email Change')], max_length=20, verbose_name='action')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created at')),
                ('expires_at', models.DateTimeField(verbose_name='expires at')),
                ('is_used', models.BooleanField(default=False, verbose_name='is used')),
                ('user', models.ForeignKey(blank=True, help_text='User associated with this OTP (can be null for registration)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='otps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'OTP',
                'verbose_name_plural': 'OTPs',
                'indexes': [models.Index(fields=['email', 'action'], name='accounts_ot_email_ed06f4_idx'), models.Index(fields=['code'], name='accounts_ot_code_e43106_idx')],
            },
        ),
    ]
