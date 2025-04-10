from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, TemplateView, UpdateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm,
    OTPVerificationForm, ResendOTPForm
)
from .models import User, OTP
from .utils import send_otp_email

class RegisterView(CreateView):
    """
    View for initiating the registration process by collecting user information.
    This now sends an OTP verification code to the email address.
    """
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    
    def form_valid(self, form):
        # BYPASS OTP: Creating user directly instead of sending OTP
        # Don't save the user yet, store data in session
        # self.request.session['registration_data'] = {
        #     'email': form.cleaned_data.get('email'),
        #     'full_name': form.cleaned_data.get('full_name'),
        #     'password1': form.cleaned_data.get('password1'),
        # }
        
        # # Send OTP to the user's email
        # email = form.cleaned_data.get('email')
        # try:
        #     send_otp_email(email, 'REGISTRATION')
        #     messages.success(self.request, _("We've sent a verification code to your email. Please check and enter the code."))
        # except Exception as e:
        #     messages.error(self.request, _("Failed to send verification code. Please try again."))
        #     return self.form_invalid(form)
        
        # # Redirect to OTP verification page
        # return redirect('verify_registration_otp')
        
        # BYPASS OTP: Create the user directly
        user = form.save()
        
        # Auto-login after registration
        authenticate_user = authenticate(
            self.request,
            email=form.cleaned_data.get('email'),
            password=form.cleaned_data.get('password1')
        )
        login(self.request, authenticate_user)
        
        # Add a success message
        messages.success(self.request, _("Registration successful! Welcome to DVM Bus Manager."))
        
        return redirect('dashboard')


class VerifyRegistrationOTPView(FormView):
    """
    View for verifying OTP during registration process.
    """
    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    
    def dispatch(self, request, *args, **kwargs):
        # Check if registration data exists in session
        if 'registration_data' not in request.session:
            messages.error(request, _("Registration session expired. Please start again."))
            return redirect('register')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['email'] = self.request.session['registration_data']['email']
        kwargs['action'] = 'REGISTRATION'
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session['registration_data']['email']
        context['action'] = 'Registration'
        context['resend_url'] = reverse('resend_registration_otp')
        return context
    
    def form_valid(self, form):
        # Get registration data from session
        registration_data = self.request.session['registration_data']
        
        # Create the user
        user = User.objects.create_user(
            email=registration_data['email'],
            full_name=registration_data['full_name'],
            password=registration_data['password1']
        )
        
        # Auto-login after registration
        authenticate_user = authenticate(
            self.request,
            email=registration_data['email'],
            password=registration_data['password1']
        )
        login(self.request, authenticate_user)
        
        # Clear session data
        if 'registration_data' in self.request.session:
            del self.request.session['registration_data']
        
        # Add a success message
        messages.success(self.request, _("Registration successful! Welcome to DVM Bus Manager."))
        
        return redirect('dashboard')


@require_http_methods(["GET", "POST"])
def resend_registration_otp(request):
    """
    View for resending OTP during registration.
    """
    if 'registration_data' not in request.session:
        messages.error(request, _("Registration session expired. Please start again."))
        return redirect('register')
    
    if request.method == 'POST':
        email = request.session['registration_data']['email']
        try:
            send_otp_email(email, 'REGISTRATION')
            messages.success(request, _("We've sent a new verification code to your email."))
        except Exception as e:
            messages.error(request, _("Failed to send verification code. Please try again."))
        
        return redirect('verify_registration_otp')
    
    # GET request
    context = {
        'email': request.session['registration_data']['email'],
        'action': 'Registration'
    }
    return render(request, 'accounts/resend_otp.html', context)


class CustomLoginView(LoginView):
    """
    Custom login view using email instead of username.
    """
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        # First call the parent class's form_valid method to log the user in
        response = super().form_valid(form)
        
        # Now the user is logged in, so we can safely access user.full_name
        # Add a success message
        messages.success(self.request, f"Welcome back, {self.request.user.full_name}!")
        
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Simple dashboard view for authenticated users.
    """
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add wallet info if it exists
        if hasattr(self.request.user, 'wallet'):
            context['wallet'] = self.request.user.wallet
            context['transactions'] = self.request.user.wallet.transactions.all()[:5]
        
        # Add booking info
        context['tickets'] = self.request.user.tickets.all()[:5]
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating user profile information.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('dashboard')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, _("Your profile has been updated successfully."))
        return super().form_valid(form)


def custom_logout(request):
    """
    Custom logout view that ensures proper logout and redirect.
    """
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    
    # Perform logout
    logout(request)
    
    # Redirect to home page
    return redirect('/')
