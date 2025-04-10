import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Django setup for template rendering
import django
from django.template.loader import render_to_string
from django.conf import settings

# SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition, ContentId

def setup_django():
    """Set up Django to allow template rendering"""
    # Add the project directory to the sys.path
    BASE_DIR = Path(__file__).resolve().parent
    sys.path.append(str(BASE_DIR))
    
    # Set up Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Bus_Booking.settings')
    django.setup()

def send_test_email(to_email, api_key, verbose=False):
    """Send a test email using the SendGrid API"""
    # Render the template
    context = {
        'year': datetime.now().year
    }
    
    email_html = render_to_string('emails/test.html', context)
    
    # Create the email
    from_email = Email(os.getenv('DEFAULT_FROM_EMAIL', 'noreply@busbliss.com'))
    to_email = To(to_email)
    subject = "DVM Bus Manager - Email Configuration Test"
    content = Content("text/html", email_html)
    
    mail = Mail(from_email, to_email, subject, content)
    
    # Send the email
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(mail)
        
        if verbose:
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.body}")
            print(f"Response Headers: {response.headers}")
        
        if response.status_code >= 200 and response.status_code < 300:
            print("✅ Email sent successfully!")
            return True
        else:
            print(f"❌ Failed to send email. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test SendGrid email delivery')
    parser.add_argument('--email', required=True, help='Recipient email address')
    parser.add_argument('--verbose', action='store_true', help='Show detailed response information')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        print("❌ SENDGRID_API_KEY not found in environment variables")
        sys.exit(1)
    
    # Setup Django for template rendering
    setup_django()
    
    # Send test email
    print(f"Sending test email to {args.email}...")
    result = send_test_email(args.email, api_key, args.verbose)
    
    if result:
        print("Email test completed successfully!")
    else:
        print("Email test failed. Check the error message above.")
        sys.exit(1) 