from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Passenger, Ticket, Bus, Wallet, Transaction, RouteSegment

class PassengerForm(forms.ModelForm):
    """
    Form for passenger details.
    """
    class Meta:
        model = Passenger
        fields = ['name', 'age', 'gender', 'id_number', 'phone']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class PassengerEditForm(forms.ModelForm):
    """
    Form for editing passenger details on an existing booking.
    """
    class Meta:
        model = Passenger
        fields = ['name', 'age', 'gender', 'id_number', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '120'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        # Allow the passenger to keep their same ID number
        if self.instance and self.instance.id_number == id_number:
            return id_number
        
        # Check if another passenger already has this ID number
        if Passenger.objects.filter(id_number=id_number).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(_("This ID number is already registered with another passenger."))
        
        return id_number
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Basic phone validation
        if not phone.isdigit():
            raise forms.ValidationError(_("Phone number must contain only digits."))
        
        if len(phone) < 10 or len(phone) > 15:
            raise forms.ValidationError(_("Phone number must be between 10 and 15 digits."))
        
        return phone


class TicketBookingForm(forms.Form):
    """
    Form for ticket booking.
    """
    segment = forms.ModelChoiceField(
        queryset=RouteSegment.objects.none(),
        empty_label=None,
        label=_("Journey Segment"),
        widget=forms.Select(attrs={
            'class': 'form-control segment-select',
        }),
        help_text=_("Select your journey segment"),
    )
    
    seat_class = forms.ChoiceField(
        label=_("Seat Class"),
        choices=Bus.SEAT_CLASS_CHOICES,
        initial='GENERAL',
        widget=forms.Select(attrs={
            'class': 'form-control seat-class-select',
        }),
        help_text=_("Select your preferred seat class. Fare varies by class."),
    )
    
    seat_numbers = forms.CharField(
        label=_("Seat Numbers"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('e.g., 1,2,3'),
        }),
        help_text=_("Enter comma-separated seat numbers."),
    )
    
    def clean_seat_numbers(self):
        seat_numbers = self.cleaned_data.get('seat_numbers')
        
        # Validate seat numbers format
        try:
            seats = [s.strip() for s in seat_numbers.split(',')]
            # Check for duplicates
            if len(seats) != len(set(seats)):
                raise forms.ValidationError(_("Duplicate seat numbers are not allowed."))
                
            # Check if all seats are valid
            for seat in seats:
                if not seat.isdigit():
                    raise forms.ValidationError(_("Seat numbers must be numeric."))
        except Exception:
            raise forms.ValidationError(_("Invalid seat numbers format. Use comma-separated numbers, e.g., '1,2,3'."))
        
        return seat_numbers
    
    def __init__(self, *args, bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If bus is provided, set available segments and seat classes
        if bus:
            # Set available segments for this bus
            if hasattr(bus, 'get_available_segments'):
                segments = bus.get_available_segments()
                self.fields['segment'].queryset = segments
            else:
                # For buses without segments, create a dummy segment
                from booking.models import RouteSegment
                # The segment field is not relevant for regular buses
                # Hide it or make it optional
                self.fields['segment'].required = False
                # Set an empty queryset
                self.fields['segment'].queryset = RouteSegment.objects.none()
            
            # Format segment choices to show cities and fare
            segment_choices = []
            for segment in segments:
                segment_label = f"{segment.start_stop.city} to {segment.end_stop.city}"
                segment_choices.append((segment.id, segment_label))
            
            # If there are segment choices, update the field
            if segment_choices:
                self.fields['segment'].choices = segment_choices
            
            # Set available seat classes based on bus configuration
            available_classes = []
            if bus.has_general_seats:
                available_classes.append(('GENERAL', _('General - ₹{}').format(bus.fare)))
            if bus.has_sleeper_seats:
                available_classes.append(('SLEEPER', _('Sleeper - ₹{}').format(bus.sleeper_fare)))
            if bus.has_luxury_seats:
                available_classes.append(('LUXURY', _('Luxury - ₹{}').format(bus.luxury_fare)))
            
            if available_classes:
                self.fields['seat_class'].choices = available_classes


class WalletDepositForm(forms.Form):
    """
    Form for depositing money into wallet.
    """
    amount = forms.DecimalField(
        label=_("Amount"),
        min_value=100,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': _('Enter amount'),
            'step': '100',
        }),
        help_text=_("Minimum deposit amount is ₹100."),
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        # Add any business rules for deposit amounts
        if amount < 100:
            raise forms.ValidationError(_("Minimum deposit amount is ₹100."))
        elif amount > 10000:
            raise forms.ValidationError(_("Maximum deposit amount is ₹10,000."))
            
        return amount


class BusSearchForm(forms.Form):
    """
    Form for searching buses by date and route.
    """
    source = forms.CharField(
        label=_("From"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Departure City'),
        }),
    )
    
    destination = forms.CharField(
        label=_("To"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Arrival City'),
        }),
    )
    
    date = forms.DateField(
        label=_("Date"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().isoformat(),
        }),
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')
        
        # Require at least one field to be filled
        if not source and not destination and not cleaned_data.get('date'):
            raise forms.ValidationError(_("Please provide at least one search criteria."))
            
        return cleaned_data


class BusForm(forms.ModelForm):
    """
    Form for creating and editing buses by admin.
    """
    class Meta:
        model = Bus
        fields = ['bus_number', 'route', 'departure_time', 
                 'arrival_time', 'fare', 'total_seats', 'available_seats', 'is_active']
        widgets = {
            'bus_number': forms.TextInput(attrs={'class': 'form-control'}),
            'route': forms.Select(attrs={'class': 'form-control'}),
            'departure_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'arrival_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'fare': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_seats': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_seats': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        departure_time = cleaned_data.get('departure_time')
        arrival_time = cleaned_data.get('arrival_time')
        total_seats = cleaned_data.get('total_seats')
        available_seats = cleaned_data.get('available_seats')
        
        # Check that departure is before arrival
        if departure_time and arrival_time and departure_time >= arrival_time:
            raise forms.ValidationError(_("Departure time must be before arrival time."))
        
        # Check that available seats don't exceed total seats
        if total_seats is not None and available_seats is not None and available_seats > total_seats:
            raise forms.ValidationError(_("Available seats cannot exceed total seats."))
        
        return cleaned_data 