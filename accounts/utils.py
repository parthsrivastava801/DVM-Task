from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import OTP

def send_otp_email(email, action, user=None, expiry_minutes=10):
    """
    Generate and send an OTP code via email
    """
    # Generate OTP
    otp = OTP.generate_otp(email, action, user, expiry_minutes)
    
    # Prepare email content
    action_readable = dict(OTP.ACTION_CHOICES).get(action, action)
    subject = f"DVM Bus Manager - Your OTP for {action_readable}"
    
    # Create context for email template
    context = {
        'otp': otp.code,
        'action': action_readable,
        'expiry_minutes': expiry_minutes,
        'user': user,
    }
    
    # Render email templates
    html_message = render_to_string('emails/otp_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    return send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@busbliss.com',
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )

def send_templated_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Send an email using an HTML template with SendGrid.
    
    Args:
        subject (str): Email subject
        template_name (str): Path to the email template (without .html extension)
        context (dict): Context data for the template
        recipient_list (list): List of email addresses to send to
        from_email (str, optional): Sender email address. Defaults to settings.DEFAULT_FROM_EMAIL.
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    # Render HTML content
    html_content = render_to_string(f'emails/{template_name}.html', context)
    
    # Create plain text version
    text_content = strip_tags(html_content)
    
    # Create email message
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=recipient_list
    )
    
    # Attach HTML content
    email.attach_alternative(html_content, "text/html")
    
    try:
        # Send email
        return email.send() > 0
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_welcome_email(user):
    """Send a welcome email to a new user"""
    context = {
        'user': user,
        'site_name': 'DVM Bus Manager',
        'login_url': f"{settings.SITE_URL}/accounts/login/" if hasattr(settings, 'SITE_URL') else '/accounts/login/'
    }
    return send_templated_email(
        subject='Welcome to DVM Bus Manager',
        template_name='welcome',
        context=context,
        recipient_list=[user.email]
    )

def send_booking_confirmation(user, booking):
    """Send a booking confirmation email"""
    context = {
        'user': user,
        'booking': booking,
        'site_name': 'DVM Bus Manager',
        'booking_url': f"{settings.SITE_URL}/booking/{booking.id}/" if hasattr(settings, 'SITE_URL') else f'/booking/{booking.id}/'
    }
    return send_templated_email(
        subject='Your DVM Bus Manager Booking Confirmation',
        template_name='booking_confirmation',
        context=context,
        recipient_list=[user.email]
    )

def send_ticket_cancellation(user, booking, refund_amount):
    """Send a ticket cancellation confirmation email"""
    context = {
        'user': user,
        'booking': booking,
        'refund_amount': refund_amount,
        'site_name': 'DVM Bus Manager'
    }
    return send_templated_email(
        subject='DVM Bus Manager Booking Cancellation Confirmation',
        template_name='booking_cancellation',
        context=context,
        recipient_list=[user.email]
    )

def send_password_reset(user, reset_url):
    """Send a password reset email"""
    context = {
        'user': user,
        'reset_url': reset_url,
        'site_name': 'DVM Bus Manager'
    }
    return send_templated_email(
        subject='Reset Your DVM Bus Manager Password',
        template_name='password_reset',
        context=context,
        recipient_list=[user.email]
    ) 