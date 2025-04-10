from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Test SendGrid email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send the test email to')

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write(self.style.WARNING('Testing SendGrid email configuration...'))
        
        # Print configuration
        self.stdout.write(f"SMTP Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"SMTP Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"Using TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"To: {recipient}")
        
        try:
            # Get HTML content from template
            context = {
                'current_year': datetime.now().year,
            }
            html_content = render_to_string('emails/test.html', context)
            text_content = strip_tags(html_content)
            
            # Create email message
            subject = 'DVM Bus Manager SendGrid Test'
            from_email = settings.DEFAULT_FROM_EMAIL
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient]
            )
            
            # Attach HTML content
            email.attach_alternative(html_content, "text/html")
            
            # Send the email
            result = email.send()
            
            if result:
                self.stdout.write(self.style.SUCCESS('Test email sent successfully!'))
                self.stdout.write(self.style.SUCCESS(f'Check your inbox at {recipient} for the test email.'))
                self.stdout.write('If you don\'t see the email, check your spam folder.')
            else:
                self.stdout.write(self.style.ERROR('Failed to send email. No error was reported, but email was not sent.'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending email: {str(e)}'))
            self.stdout.write(self.style.WARNING('\nTroubleshooting steps:'))
            self.stdout.write('1. Make sure your SendGrid API key is correct')
            self.stdout.write('2. Verify that the API key has the necessary permissions')
            self.stdout.write('3. Check if your SendGrid account is active')
            self.stdout.write('4. Ensure your from_email address is verified in SendGrid')
            self.stdout.write('5. Try sending from a different email address') 