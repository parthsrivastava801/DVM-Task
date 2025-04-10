from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages

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
    
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # Get information from the social account
        if sociallogin.account.provider == 'google':
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
                
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Check if this social account is already connected to a user
        """
        # If email exists in the system but not connected to this social account
        if sociallogin.is_existing:
            return
        
        # Check if we already have a user with this email
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
            try:
                user = self.get_model('User').objects.get(email=email)
                
                # Connect the social account to the existing user
                sociallogin.connect(request, user)
                
                # Show a message to the user
                messages.success(request, "Your Google account has been connected to your existing DVM Bus Manager account.")
                
                # Skip the signup form
                raise ImmediateHttpResponse(redirect(settings.LOGIN_REDIRECT_URL))
                
            except self.get_model('User').DoesNotExist:
                # User doesn't exist yet, continue with normal signup process
                pass 