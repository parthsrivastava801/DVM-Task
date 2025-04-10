from allauth.socialaccount.models import SocialApp
from django.conf import settings

def social_auth_config(request):
    """
    Add social auth configuration status to context.
    """
    context = {
        'google_oauth_configured': False,
    }
    
    # Check if Google is in the SOCIALACCOUNT_PROVIDERS setting
    if hasattr(settings, 'SOCIALACCOUNT_PROVIDERS') and 'google' in settings.SOCIALACCOUNT_PROVIDERS:
        # Check if there's a configured Google SocialApp
        try:
            google_app = SocialApp.objects.filter(provider='google').exists()
            context['google_oauth_configured'] = google_app
        except:
            pass
    
    return context 