from django.urls import path, re_path
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView
)
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from . import views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

urlpatterns = [
    # Authentication URLs
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-otp/', views.VerifyRegistrationOTPView.as_view(), name='verify_registration_otp'),
    path('resend-otp/', views.resend_registration_otp, name='resend_registration_otp'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Dashboard and Profile URLs
    path('dashboard/', login_required(views.DashboardView.as_view()), name='dashboard'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    
    # Password reset URLs
    path('password-reset/', 
         PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             form_class=CustomPasswordResetForm,
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', 
         PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             form_class=CustomSetPasswordForm,
             success_url='/accounts/password-reset/complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Password change URLs (for logged in users)
    path('password-change/', 
         PasswordChangeView.as_view(
             template_name='accounts/password_change.html',
             success_url='/accounts/password-change/done/'
         ), 
         name='password_change'),
    path('password-change/done/', 
         PasswordChangeDoneView.as_view(
             template_name='accounts/password_change_done.html'
         ), 
         name='password_change_done'),

    path('debug/oauth-status/', views.debug_oauth_status, name='debug_oauth_status'),  # Debugging endpoint
    
    # Catch-all for the Google callback path with trailing parts
    re_path(r'^google/login/callback/.*$', lambda request: redirect('/accounts/dashboard/')),
] 