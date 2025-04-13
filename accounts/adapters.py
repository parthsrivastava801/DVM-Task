from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
import logging

# Set up logging
logger = logging.getLogger(__name__)

class DVMBusManagerAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Allow all signups
        return True
    
    def get_login_redirect_url(self, request):
        # Customize redirection after login
        return settings.LOGIN_REDIRECT_URL

class DVMBusManagerSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        # Allow social account signups
        return True
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after successfully connecting a social account.
        """
        logger.info(f"Social account connection successful, redirecting to dashboard")
        return settings.LOGIN_REDIRECT_URL
    
    def get_login_redirect_url(self, request):
        """
        Returns the URL to redirect to after successful authentication.
        """
        logger.info(f"Social login successful, redirecting to dashboard")
        return settings.LOGIN_REDIRECT_URL
    
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # Get information from the social account
        if sociallogin.account.provider == 'google':
            try:
                # Get full name from Google data
                if sociallogin.account.extra_data.get('name'):
                    user.full_name = sociallogin.account.extra_data.get('name')
                
                # If we have separate first and last name fields
                elif sociallogin.account.extra_data.get('given_name') and sociallogin.account.extra_data.get('family_name'):
                    given_name = sociallogin.account.extra_data.get('given_name', '')
                    family_name = sociallogin.account.extra_data.get('family_name', '')
                    user.full_name = f"{given_name} {family_name}".strip()
                
                # Get profile picture if available
                if sociallogin.account.extra_data.get('picture'):
                    # Store profile URL if your user model has a field for it
                    user.profile_picture_url = sociallogin.account.extra_data.get('picture')
            except Exception as e:
                logger.error(f"Error populating user data from Google: {str(e)}")
                
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Custom save_user to handle any edge cases during user creation
        """
        try:
            user = super().save_user(request, sociallogin, form)
            logger.info(f"Successfully created user {user.email} via {sociallogin.account.provider}")
            return user
        except Exception as e:
            logger.error(f"Error creating user via social login: {str(e)}")
            # Re-raise to let allauth handle the error
            raise
    
    def pre_social_login(self, request, sociallogin):
        """
        Check if this social account is already connected to a user
        """
        try:
            # If email exists in the system but not connected to this social account
            if sociallogin.is_existing:
                return
            
            # Log the social account information for debugging
            provider = sociallogin.account.provider
            logger.info(f"Processing pre_social_login for {provider}")
            
            # Check if we already have a user with this email
            if sociallogin.email_addresses and sociallogin.email_addresses[0].verified:
                email = sociallogin.email_addresses[0].email
                logger.info(f"Checking for existing user with email: {email}")
                
                User = get_user_model()
                try:
                    user = User.objects.get(email=email)
                    logger.info(f"Found existing user: {user.email}")
                    
                    # Connect the social account to the existing user
                    sociallogin.connect(request, user)
                    
                    # Show a message to the user
                    messages.success(request, f"Your {provider.title()} account has been connected to your existing DVM Bus Manager account.")
                    
                    # Skip the signup form using the absolute URL path
                    dashboard_url = settings.LOGIN_REDIRECT_URL
                    logger.info(f"Redirecting to: {dashboard_url}")
                    raise ImmediateHttpResponse(redirect(dashboard_url))
                    
                except User.DoesNotExist:
                    # User doesn't exist yet, continue with normal signup process
                    logger.info(f"No existing user found with email {email}, proceeding with new account creation")
                    pass
            else:
                logger.warning("Email address not provided or not verified by social provider")
        except Exception as e:
            logger.error(f"Error in pre_social_login: {str(e)}")
            # Just continue with the normal flow, don't raise an error 