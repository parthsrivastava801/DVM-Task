from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import random
import string
from datetime import timedelta

class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_passenger', False)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, full_name, password, **extra_fields)

class User(AbstractUser):
    """
    Custom User model using email as the primary identifier instead of username.
    """
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    full_name = models.CharField(_('full name'), max_length=150)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_passenger = models.BooleanField(default=True)
    profile_picture_url = models.URLField(_('profile picture URL'), max_length=1000, blank=True, null=True)
    
    # If staff flag is set to True, user becomes an admin
    # This will be done manually in the admin interface
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        
    def __str__(self):
        return self.email


class OTP(models.Model):
    """
    Model to store One-Time Passwords for various actions
    """
    ACTION_CHOICES = (
        ('REGISTRATION', _('Registration')),
        ('BOOKING', _('Booking')),
        ('PASSWORD_RESET', _('Password Reset')),
        ('EMAIL_CHANGE', _('Email Change')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                             related_name='otps', help_text=_('User associated with this OTP (can be null for registration)'))
    email = models.EmailField(_('email address'))
    code = models.CharField(_('OTP code'), max_length=6)
    action = models.CharField(_('action'), max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    expires_at = models.DateTimeField(_('expires at'))
    is_used = models.BooleanField(_('is used'), default=False)
    
    class Meta:
        verbose_name = _('OTP')
        verbose_name_plural = _('OTPs')
        indexes = [
            models.Index(fields=['email', 'action']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"OTP for {self.email} ({self.action})"
    
    @classmethod
    def generate_otp(cls, email, action, user=None, expiry_minutes=10):
        """
        Generate a new OTP for the specified email and action
        """
        # Invalidate any existing OTPs for this email and action
        cls.objects.filter(email=email, action=action, is_used=False).update(is_used=True)
        
        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Create and return the new OTP
        return cls.objects.create(
            user=user, 
            email=email, 
            code=code, 
            action=action, 
            expires_at=expires_at
        )
    
    @classmethod
    def verify_otp(cls, email, action, code):
        """
        Verify if the provided OTP is valid for the email and action
        """
        # BYPASS OTP: Always return True for bypassing OTP verification
        # Change to False to re-enable OTP verification 
        BYPASS_OTP_VERIFICATION = True
        
        if BYPASS_OTP_VERIFICATION:
            # Return a successful verification without checking
            return True, None
            
        # Normal OTP verification (not used when bypassing is enabled)
        try:
            otp = cls.objects.get(
                email=email,
                action=action,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            # Mark as used
            otp.is_used = True
            otp.save()
            return True, otp
        except cls.DoesNotExist:
            return False, None
