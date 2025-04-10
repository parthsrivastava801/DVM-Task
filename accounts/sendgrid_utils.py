import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_email_with_sendgrid(to_email, subject, template_name, context=None):
    """
    Send an email using SendGrid's API directly (not SMTP)
    
    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        template_name (str): Name of the template file in templates/emails/
        context (dict): Context data for the template
    
    Returns:
        bool: True if successful, False if failed
    """
    if context is None:
        context = {}
        
    # Get API key from settings or environment
    api_key = os.environ.get('SENDGRID_API_KEY') or settings.EMAIL_HOST_PASSWORD
    
    # Get from email from settings
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        # Render email content from template
        html_content = render_to_string(f'emails/{template_name}.html', context)
        plain_content = strip_tags(html_content)
        
        # Create SendGrid client
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        
        # Create mail object
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Send email
        response = sg.send(message)
        
        # Log response
        print(f"SendGrid response status code: {response.status_code}")
        
        # Return True if successful (2xx status code)
        return 200 <= response.status_code < 300
        
    except Exception as e:
        print(f"Error sending email via SendGrid API: {str(e)}")
        return False

def send_test_email(to_email):
    """Send a test email using the SendGrid API"""
    from datetime import datetime
    context = {
        'current_year': datetime.now().year,
    }
    return send_email_with_sendgrid(
        to_email=to_email,
        subject='DVM Bus Manager - SendGrid API Test',
        template_name='test',
        context=context
    )

def send_welcome_email(user):
    """Send a welcome email to a new user"""
    context = {
        'user': user,
        'site_name': 'DVM Bus Manager',
        'login_url': f"{settings.SITE_URL}/accounts/login/" if hasattr(settings, 'SITE_URL') else '/accounts/login/'
    }
    return send_email_with_sendgrid(
        to_email=user.email,
        subject='Welcome to DVM Bus Manager',
        template_name='welcome',
        context=context
    )

def send_booking_confirmation(user, booking):
    """Send a booking confirmation email"""
    context = {
        'user': user,
        'booking': booking,
        'site_name': 'DVM Bus Manager',
        'booking_url': f"{settings.SITE_URL}/booking/{booking.id}/" if hasattr(settings, 'SITE_URL') else f'/booking/{booking.id}/'
    }
    return send_email_with_sendgrid(
        to_email=user.email,
        subject='Your DVM Bus Manager Booking Confirmation',
        template_name='booking_confirmation',
        context=context
    )

def send_otp_email(email, code, action, expiry_minutes=10):
    """Send OTP verification email"""
    context = {
        'code': code,
        'action': action,
        'expiry_minutes': expiry_minutes,
    }
    return send_email_with_sendgrid(
        to_email=email,
        subject=f'DVM Bus Manager - Your OTP for {action}',
        template_name='otp_email',
        context=context
    ) 