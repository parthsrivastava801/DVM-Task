from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send the test email to')

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write(self.style.WARNING('Testing email configuration...'))
        self.stdout.write(f"FROM: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"TO: {recipient}")
        self.stdout.write(f"SMTP Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"SMTP Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"TLS Enabled: {settings.EMAIL_USE_TLS}")
        
        try:
            send_mail(
                subject='DVM Bus Manager Email Configuration Test',
                message='This is a test email from DVM Bus Manager to verify your SMTP configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Test email sent successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
            sys.exit(1) 