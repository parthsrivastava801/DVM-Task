from django import template
from allauth.socialaccount import providers
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def is_social_provider_available(provider_id):
    """
    Check if a specific social provider is available in the database.
    Returns True if the provider is available, False otherwise.
    """
    for provider in providers.registry.get_list():
        if provider.id == provider_id:
            return True
    return False

@register.simple_tag
def safe_google_button(process=None):
    """
    Renders a Google sign-in button only if Google provider is available.
    """
    is_available = False
    for provider in providers.registry.get_list():
        if provider.id == 'google':
            is_available = True
            break
    
    if is_available:
        process_param = f" process='{process}'" if process else ""
        return mark_safe(f'<a href="{{% provider_login_url \'google\'{process_param} %}}" class="btn btn-outline-danger">' +
                        '<img src="{% static \'images/google-icon.png\' %}" alt="Google" width="20" height="20" class="me-2" onerror="this.style.display=\'none\'">' +
                        f'Sign {"up" if process=="signup" else "in"} with Google</a>')
    else:
        return mark_safe('<a href="#" class="btn btn-outline-secondary disabled">Google Sign-in Currently Unavailable</a>') 