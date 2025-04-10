from accounts.models import OTP
from accounts.utils import send_otp_email
from django.utils.translation import gettext_lazy as _


def send_booking_otp(user, bus_id, booking_data=None):
    """
    Send a booking verification OTP to the user's email
    
    Args:
        user: The User object
        bus_id: ID of the bus being booked
        booking_data: Dictionary with additional booking data to store in session
        
    Returns:
        Boolean indicating success/failure
    """
    try:
        # Generate and send OTP
        send_otp_email(user.email, 'BOOKING', user, expiry_minutes=5)
        return True
    except Exception as e:
        # Log the error here
        return False 