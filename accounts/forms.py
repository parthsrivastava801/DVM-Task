from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.utils.translation import gettext_lazy as _

from .models import User, OTP

class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users with email as the primary identifier.
    """
    class Meta:
        model = User
        fields = ('email', 'full_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email'})
        self.fields['full_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Full Name'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})


class CustomAuthenticationForm(AuthenticationForm):
    """
    A form for authenticating users with email and password.
    """
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class UserProfileForm(forms.ModelForm):
    """
    A form for users to update their profile information.
    """
    class Meta:
        model = User
        fields = ('full_name', 'email')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].disabled = True  # Email cannot be changed


class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form with Bootstrap styling.
    """
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )


class CustomSetPasswordForm(SetPasswordForm):
    """
    Custom password change form with Bootstrap styling.
    """
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
    )


class OTPVerificationForm(forms.Form):
    """
    Form for verifying OTP codes.
    """
    otp_code = forms.CharField(
        label=_("OTP Code"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter 6-digit OTP code'),
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code'
        })
    )
    
    def __init__(self, *args, email=None, action=None, **kwargs):
        self.email = email
        self.action = action
        super().__init__(*args, **kwargs)
    
    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code')
        
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError(_("OTP code must be a 6-digit number."))
        
        # Verify OTP if email and action are provided
        if self.email and self.action:
            valid, otp = OTP.verify_otp(self.email, self.action, code)
            if not valid:
                raise forms.ValidationError(_("Invalid or expired OTP code. Please request a new one."))
        
        return code


class ResendOTPForm(forms.Form):
    """
    Form for resending OTP codes.
    """
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email'),
        })
    )
    
    def __init__(self, *args, action=None, **kwargs):
        self.action = action
        super().__init__(*args, **kwargs) 