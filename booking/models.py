from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Q
from django.db.models.query import EmptyQuerySet
from itertools import chain


class Route(models.Model):
    """
    Simple Route model for bus journeys from one city to another.
    """
    origin = models.CharField(_('origin city'), max_length=100)
    destination = models.CharField(_('destination city'), max_length=100)
    distance = models.DecimalField(_('distance (km)'), max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_duration = models.DurationField(_('estimated journey time'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('route')
        verbose_name_plural = _('routes')
        unique_together = ('origin', 'destination')
    
    def __str__(self):
        return f"{self.origin} to {self.destination}"


class MultiStopRoute(models.Model):
    """
    Route model for bus journeys with multiple stops.
    """
    name = models.CharField(_('route name'), max_length=100)
    description = models.TextField(_('description'), blank=True, null=True)
    is_active = models.BooleanField(_('is active'), default=True)
    
    class Meta:
        verbose_name = _('multi-stop route')
        verbose_name_plural = _('multi-stop routes')
    
    def __str__(self):
        stops = self.stops.all().order_by('sequence')
        if stops.exists():
            first_stop = stops.first().city
            last_stop = stops.last().city
            return f"{first_stop} to {last_stop} via {stops.count()-2} stops"
        return self.name
    
    @property
    def total_distance(self):
        """Get the total distance of the entire route"""
        segments = self.segments.all()
        return sum(segment.distance for segment in segments if segment.distance)
    
    def get_stops_ordered(self):
        """Get all stops in sequence order"""
        return self.stops.all().order_by('sequence')
    
    def get_segments_ordered(self):
        """Get all segments in sequence order"""
        return self.segments.all().order_by('start_stop__sequence')


class RouteStop(models.Model):
    """
    Model representing a stop in a route.
    """
    route = models.ForeignKey(MultiStopRoute, on_delete=models.CASCADE, related_name='stops')
    city = models.CharField(_('city name'), max_length=100)
    sequence = models.PositiveIntegerField(_('stop sequence'))
    arrival_offset = models.DurationField(_('arrival time offset'), null=True, blank=True,
                                        help_text=_("Time offset from route start for arrival"))
    departure_offset = models.DurationField(_('departure time offset'), null=True, blank=True,
                                          help_text=_("Time offset from route start for departure"))
    is_boarding_point = models.BooleanField(_('is boarding point'), default=True)
    is_dropping_point = models.BooleanField(_('is dropping point'), default=True)
    
    class Meta:
        verbose_name = _('route stop')
        verbose_name_plural = _('route stops')
        unique_together = ('route', 'sequence')
        ordering = ['route', 'sequence']
    
    def __str__(self):
        return f"{self.city} (Stop #{self.sequence})"
    
    def get_arrival_time(self, bus_departure_time):
        """Calculate actual arrival time based on bus departure and offset"""
        if self.arrival_offset:
            return bus_departure_time + self.arrival_offset
        return None
    
    def get_departure_time(self, bus_departure_time):
        """Calculate actual departure time based on bus departure and offset"""
        if self.departure_offset:
            return bus_departure_time + self.departure_offset
        return None


class RouteSegment(models.Model):
    """
    Model representing a segment between two consecutive stops in a route.
    """
    route = models.ForeignKey(MultiStopRoute, on_delete=models.CASCADE, related_name='segments')
    start_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='departing_segments')
    end_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='arriving_segments')
    distance = models.DecimalField(_('distance (km)'), max_digits=8, decimal_places=2, null=True, blank=True)
    duration = models.DurationField(_('estimated journey time'), null=True, blank=True)
    base_fare_multiplier = models.DecimalField(_('base fare multiplier'), max_digits=3, decimal_places=2, default=1.0,
                                             help_text=_("Multiplier applied to the bus base fare for this segment"))
    
    class Meta:
        verbose_name = _('route segment')
        verbose_name_plural = _('route segments')
        unique_together = ('route', 'start_stop', 'end_stop')
    
    def __str__(self):
        return f"{self.start_stop.city} to {self.end_stop.city}"
    
    def get_fare_for_bus(self, bus):
        """Calculate fare for this segment based on bus base fare and multiplier"""
        return bus.fare * self.base_fare_multiplier
    
    def get_departure_time(self, bus_departure_time):
        """Get departure time for this segment based on bus departure time"""
        return self.start_stop.get_departure_time(bus_departure_time)
    
    def get_arrival_time(self, bus_departure_time):
        """Get arrival time for this segment based on bus departure time"""
        return self.end_stop.get_arrival_time(bus_departure_time)


class MultiStopBus(models.Model):
    """
    Bus model with route, timings, and seat details for multi-stop routes.
    """
    # Seat class choices
    SEAT_CLASS_CHOICES = (
        ('GENERAL', _('General')),
        ('SLEEPER', _('Sleeper')),
        ('LUXURY', _('Luxury')),
    )
    
    route = models.ForeignKey(MultiStopRoute, on_delete=models.CASCADE, related_name='buses')
    bus_number = models.CharField(_('bus number'), max_length=20, unique=True)
    departure_time = models.DateTimeField(_('departure time'))
    arrival_time = models.DateTimeField(_('arrival time'))
    
    # Seat information
    total_seats = models.PositiveIntegerField(_('total seats'), 
                                             validators=[MinValueValidator(1)])
    available_seats = models.PositiveIntegerField(_('available seats'), 
                                                 validators=[MinValueValidator(0)])
    
    # Base fare (for General class)
    fare = models.DecimalField(_('base fare'), max_digits=10, decimal_places=2)
    
    # Additional seat class fares
    sleeper_fare = models.DecimalField(_('sleeper fare'), max_digits=10, decimal_places=2, null=True, blank=True)
    luxury_fare = models.DecimalField(_('luxury fare'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Seat class availability
    has_general_seats = models.BooleanField(_('has general seats'), default=True)
    has_sleeper_seats = models.BooleanField(_('has sleeper seats'), default=False)
    has_luxury_seats = models.BooleanField(_('has luxury seats'), default=False)
    
    is_active = models.BooleanField(_('is active'), default=True)
    
    class Meta:
        verbose_name = _('multi-stop bus')
        verbose_name_plural = _('multi-stop buses')
        ordering = ['departure_time']
    
    def __str__(self):
        stops = self.route.stops.all().order_by('sequence')
        if stops.exists():
            first_stop = stops.first().city
            last_stop = stops.last().city
            return f"{self.bus_number} - {first_stop} to {last_stop} ({self.departure_time.strftime('%d %b %Y, %H:%M')})"
        return f"{self.bus_number} - {self.route.name} ({self.departure_time.strftime('%d %b %Y, %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Ensure available seats never exceed total seats
        if self.available_seats > self.total_seats:
            self.available_seats = self.total_seats
        
        # Set default values for sleeper and luxury fares if not provided
        if self.has_sleeper_seats and not self.sleeper_fare:
            self.sleeper_fare = self.fare * 1.5  # 50% more than base fare
        
        if self.has_luxury_seats and not self.luxury_fare:
            self.luxury_fare = self.fare * 2.0  # Double the base fare
            
        super().save(*args, **kwargs)
    
    @property
    def is_full(self):
        return self.available_seats == 0
    
    @property
    def seats_taken(self):
        return self.total_seats - self.available_seats
    
    @property
    def journey_duration(self):
        if self.arrival_time and self.departure_time:
            return self.arrival_time - self.departure_time
        return None
    
    def get_fare_for_class(self, seat_class):
        """
        Get the fare for a specific seat class.
        """
        if seat_class == 'SLEEPER' and self.has_sleeper_seats:
            return self.sleeper_fare
        elif seat_class == 'LUXURY' and self.has_luxury_seats:
            return self.luxury_fare
        else:
            return self.fare  # Default to general fare
    
    def calculate_segment_fare(self, segment, seat_class='GENERAL'):
        """
        Calculate fare for a specific segment and seat class.
        """
        base_fare = self.get_fare_for_class(seat_class)
        segment_fare = base_fare * Decimal(segment.base_fare_multiplier)
        return segment_fare
    
    def get_available_segments(self):
        """
        Get all available segments for this bus.
        """
        return self.route.segments.all().order_by('start_stop__sequence')
    
    def get_segment_availability(self, segment):
        """
        Check seat availability for a specific segment.
        Takes into account overlapping bookings on other segments.
        """
        # Get all tickets for this bus
        booked_tickets = MultiStopTicket.objects.filter(bus=self, status='BOOKED')
        
        # Count seats booked on this segment or overlapping segments
        booked_seats_count = 0
        for ticket in booked_tickets:
            # Check if the ticket's segment overlaps with the requested segment
            if (ticket.start_stop.sequence <= segment.end_stop.sequence and 
                ticket.end_stop.sequence >= segment.start_stop.sequence):
                booked_seats_count += ticket.passenger_count
        
        return self.total_seats - booked_seats_count


class Bus(models.Model):
    """
    Bus model with route, timings, and seat details.
    """
    # Seat class choices
    SEAT_CLASS_CHOICES = (
        ('GENERAL', _('General')),
        ('SLEEPER', _('Sleeper')),
        ('LUXURY', _('Luxury')),
    )
    
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='buses')
    bus_number = models.CharField(_('bus number'), max_length=20, unique=True)
    departure_time = models.DateTimeField(_('departure time'))
    arrival_time = models.DateTimeField(_('arrival time'))
    
    # Seat information
    total_seats = models.PositiveIntegerField(_('total seats'), 
                                             validators=[MinValueValidator(1)])
    available_seats = models.PositiveIntegerField(_('available seats'), 
                                                 validators=[MinValueValidator(0)])
    
    # Base fare (for General class)
    fare = models.DecimalField(_('base fare'), max_digits=10, decimal_places=2)
    
    # Additional seat class fares
    sleeper_fare = models.DecimalField(_('sleeper fare'), max_digits=10, decimal_places=2, null=True, blank=True)
    luxury_fare = models.DecimalField(_('luxury fare'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Seat class availability
    has_general_seats = models.BooleanField(_('has general seats'), default=True)
    has_sleeper_seats = models.BooleanField(_('has sleeper seats'), default=False)
    has_luxury_seats = models.BooleanField(_('has luxury seats'), default=False)
    
    is_active = models.BooleanField(_('is active'), default=True)
    
    class Meta:
        verbose_name = _('bus')
        verbose_name_plural = _('buses')
        ordering = ['departure_time']
    
    def __str__(self):
        return f"{self.bus_number} - {self.route} ({self.departure_time.strftime('%d %b %Y, %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Ensure available seats never exceed total seats
        if self.available_seats > self.total_seats:
            self.available_seats = self.total_seats
        
        # Set default values for sleeper and luxury fares if not provided
        if self.has_sleeper_seats and not self.sleeper_fare:
            self.sleeper_fare = self.fare * 1.5  # 50% more than base fare
        
        if self.has_luxury_seats and not self.luxury_fare:
            self.luxury_fare = self.fare * 2.0  # Double the base fare
            
        super().save(*args, **kwargs)
    
    @property
    def is_full(self):
        return self.available_seats == 0
    
    @property
    def seats_taken(self):
        return self.total_seats - self.available_seats
    
    @property
    def journey_duration(self):
        if self.arrival_time and self.departure_time:
            return self.arrival_time - self.departure_time
        return None
    
    def get_fare_for_class(self, seat_class):
        """
        Get the fare for a specific seat class.
        """
        if seat_class == 'SLEEPER' and self.has_sleeper_seats:
            return self.sleeper_fare
        elif seat_class == 'LUXURY' and self.has_luxury_seats:
            return self.luxury_fare
        else:
            return self.fare  # Default to general fare
    
    def get_available_segments(self):
        """
        Returns all available segments for this bus.
        For compatibility with the form.
        """
        # Most buses don't have segments directly
        # This is a compatibility method for the booking form
        from booking.models import RouteSegment
        return RouteSegment.objects.none()


class Passenger(models.Model):
    """
    Passenger details for tickets.
    """
    GENDER_CHOICES = (
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
    )
    
    name = models.CharField(_('full name'), max_length=100)
    age = models.PositiveIntegerField(_('age'))
    gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES)
    id_number = models.CharField(_('ID number'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    
    class Meta:
        verbose_name = _('passenger')
        verbose_name_plural = _('passengers')
    
    def __str__(self):
        return f"{self.name} ({self.age})"


class Wallet(models.Model):
    """
    Wallet model for users to store and use funds for bookings.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(_('balance'), max_digits=10, decimal_places=2, default=0.00,
                                 validators=[MinValueValidator(0.00)])
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('wallet')
        verbose_name_plural = _('wallets')
    
    def __str__(self):
        return f"{self.user.email}'s Wallet (₹{self.balance})"
    
    def deposit(self, amount, description=None):
        """Add funds to wallet"""
        if amount <= 0:
            return False
        
        # Ensure amount is a Decimal
        if not isinstance(amount, Decimal):
            amount = Decimal(str(float(amount)))
        
        self.balance += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='DEPOSIT',
            description=description or f"Deposit of ₹{amount}"
        )
        
        return True
    
    def withdraw(self, amount):
        """Withdraw funds from wallet"""
        if amount <= 0 or amount > self.balance:
            return False
        
        # Ensure amount is a Decimal
        if not isinstance(amount, Decimal):
            amount = Decimal(str(float(amount)))
        
        self.balance -= amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='WITHDRAW',
            description=f"Withdrawal of ₹{amount}"
        )
        
        return True
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has sufficient balance"""
        return self.balance >= amount


class Transaction(models.Model):
    """
    Transaction model to track wallet operations.
    """
    TRANSACTION_TYPES = (
        ('DEPOSIT', _('Deposit')),
        ('WITHDRAW', _('Withdrawal')),
        ('PAYMENT', _('Payment')),
        ('REFUND', _('Refund')),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    transaction_type = models.CharField(_('transaction type'), max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(_('description'), max_length=255, blank=True)
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)
    related_ticket = models.ForeignKey('Ticket', on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='transactions')
    related_multistop_ticket = models.ForeignKey('MultiStopTicket', on_delete=models.SET_NULL, null=True, blank=True, 
                                               related_name='transactions')
    
    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.timestamp.strftime('%d %b %Y, %H:%M')}"


class Ticket(models.Model):
    """
    Ticket model linking users to buses with passenger details.
    """
    STATUS_CHOICES = (
        ('BOOKED', _('Booked')),
        ('CANCELLED', _('Cancelled')),
        ('COMPLETED', _('Completed')),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='tickets')
    booking_time = models.DateTimeField(_('booking time'), default=timezone.now)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    passengers = models.ManyToManyField(Passenger, related_name='tickets')
    total_fare = models.DecimalField(_('total fare'), max_digits=10, decimal_places=2)
    seat_numbers = models.CharField(_('seat numbers'), max_length=255, help_text="Comma-separated seat numbers")
    seat_class = models.CharField(_('seat class'), max_length=20, choices=Bus.SEAT_CLASS_CHOICES, default='GENERAL')
    
    # For multi-stop routes - optional fields
    start_stop = models.ForeignKey('RouteStop', null=True, blank=True, on_delete=models.SET_NULL, related_name='departing_tickets')
    end_stop = models.ForeignKey('RouteStop', null=True, blank=True, on_delete=models.SET_NULL, related_name='arriving_tickets')
    
    class Meta:
        verbose_name = _('ticket')
        verbose_name_plural = _('tickets')
        ordering = ['-booking_time']
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.user.email} - {self.bus.bus_number}"
    
    @property
    def passenger_count(self):
        return self.passengers.count()
    
    def cancel(self):
        """Cancel the ticket and update available seats."""
        if self.status == 'BOOKED':
            self.status = 'CANCELLED'
            self.bus.available_seats += self.passenger_count
            self.bus.save()
            self.save()
            
            # Process refund to wallet
            try:
                wallet = self.user.wallet
                wallet.deposit(self.total_fare)
                
                # Update transaction description
                latest_transaction = wallet.transactions.latest('timestamp')
                latest_transaction.transaction_type = 'REFUND'
                latest_transaction.description = f"Refund for cancelled ticket #{self.id}"
                latest_transaction.related_ticket = self
                latest_transaction.save()
                
            except Wallet.DoesNotExist:
                # If user doesn't have a wallet, create one and deposit refund
                wallet = Wallet.objects.create(user=self.user)
                wallet.deposit(self.total_fare)
                
                # Update transaction
                latest_transaction = wallet.transactions.latest('timestamp')
                latest_transaction.transaction_type = 'REFUND'
                latest_transaction.description = f"Refund for cancelled ticket #{self.id}"
                latest_transaction.related_ticket = self
                latest_transaction.save()
            
            return True
        return False
    
    def book_with_wallet(self):
        """
        Process payment for this ticket using the user's wallet.
        """
        try:
            wallet = self.user.wallet
            if wallet.has_sufficient_balance(self.total_fare):
                # Create a transaction for the payment
                transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=self.total_fare,
                    transaction_type='PAYMENT',
                    description=f"Payment for ticket #{self.id} - {self.bus.bus_number}",
                    related_ticket=self
                )
                
                # Deduct amount from wallet
                return wallet.withdraw(self.total_fare)
            return False
        except Exception:
            return False
    
    def cancel_and_refund(self):
        """
        Cancel this ticket and process refund to user's wallet.
        """
        try:
            # Only process if ticket is in BOOKED status
            if self.status != 'BOOKED':
                return False
            
            # Check refund eligibility based on departure time
            hours_to_departure = (self.bus.departure_time - timezone.now()).total_seconds() / 3600
            
            # Determine refund amount based on cancellation time
            if hours_to_departure >= 24:  # Full refund if >= 24 hours before departure
                refund_percentage = 1.0
            elif hours_to_departure >= 12:  # 75% refund if >= 12 hours before departure
                refund_percentage = 0.75
            elif hours_to_departure >= 6:  # 50% refund if >= 6 hours before departure
                refund_percentage = 0.5
            else:  # 25% refund if < 6 hours before departure
                refund_percentage = 0.25
            
            refund_amount = self.total_fare * refund_percentage
            
            # Process refund
            wallet = self.user.wallet
            wallet.deposit(refund_amount)
            
            # Create transaction record for the refund
            Transaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='REFUND',
                description=f"Refund for cancelled ticket #{self.id} - {self.bus.bus_number} ({int(refund_percentage*100)}%)",
                related_ticket=self
            )
            
            # Update bus available seats
            seat_count = self.passenger_count
            self.bus.available_seats += seat_count
            self.bus.save()
            
            # Mark ticket as cancelled
            self.status = 'CANCELLED'
            self.save()
            
            return True
        except Exception:
            return False


class MultiStopTicket(models.Model):
    """
    Ticket model linking users to multi-stop buses with passenger details and segment information.
    """
    STATUS_CHOICES = (
        ('BOOKED', _('Booked')),
        ('CANCELLED', _('Cancelled')),
        ('COMPLETED', _('Completed')),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='multistop_tickets')
    bus = models.ForeignKey(MultiStopBus, on_delete=models.PROTECT, related_name='tickets')
    
    # Segment information for partial route booking
    start_stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name='departure_tickets')
    end_stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name='arrival_tickets')
    
    booking_time = models.DateTimeField(_('booking time'), default=timezone.now)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    passengers = models.ManyToManyField(Passenger, related_name='multistop_tickets')
    total_fare = models.DecimalField(_('total fare'), max_digits=10, decimal_places=2)
    seat_numbers = models.CharField(_('seat numbers'), max_length=255, help_text="Comma-separated seat numbers")
    seat_class = models.CharField(_('seat class'), max_length=20, choices=MultiStopBus.SEAT_CLASS_CHOICES, default='GENERAL')
    
    class Meta:
        verbose_name = _('multi-stop ticket')
        verbose_name_plural = _('multi-stop tickets')
        ordering = ['-booking_time']
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.user.email} - {self.bus.bus_number} ({self.start_stop.city} to {self.end_stop.city})"
    
    @property
    def passenger_count(self):
        return self.passengers.count()
    
    @property
    def segment_description(self):
        """Get a description of the booked segment"""
        return f"{self.start_stop.city} to {self.end_stop.city}"
    
    @property
    def departure_time(self):
        """Get the departure time from the starting stop"""
        return self.start_stop.get_departure_time(self.bus.departure_time)
    
    @property
    def arrival_time(self):
        """Get the arrival time at the ending stop"""
        return self.end_stop.get_arrival_time(self.bus.departure_time)
    
    def cancel(self):
        """Cancel the ticket and update available seats."""
        if self.status == 'BOOKED':
            self.status = 'CANCELLED'
            self.bus.available_seats += self.passenger_count
            self.bus.save()
            self.save()
            
            # Process refund to wallet
            try:
                wallet = self.user.wallet
                wallet.deposit(self.total_fare)
                
                # Update transaction description
                latest_transaction = wallet.transactions.latest('timestamp')
                latest_transaction.transaction_type = 'REFUND'
                latest_transaction.description = f"Refund for cancelled ticket #{self.id}"
                latest_transaction.related_multistop_ticket = self
                latest_transaction.save()
                
            except Wallet.DoesNotExist:
                # If user doesn't have a wallet, create one and deposit refund
                wallet = Wallet.objects.create(user=self.user)
                wallet.deposit(self.total_fare)
                
                # Update transaction
                latest_transaction = wallet.transactions.latest('timestamp')
                latest_transaction.transaction_type = 'REFUND'
                latest_transaction.description = f"Refund for cancelled ticket #{self.id}"
                latest_transaction.related_multistop_ticket = self
                latest_transaction.save()
            
            return True
        return False
    
    def book_with_wallet(self):
        """
        Process payment for this ticket using the user's wallet.
        """
        try:
            wallet = self.user.wallet
            if wallet.has_sufficient_balance(self.total_fare):
                # Create a transaction for the payment
                transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=self.total_fare,
                    transaction_type='PAYMENT',
                    description=f"Payment for ticket #{self.id} - {self.bus.bus_number} ({self.segment_description})",
                    related_multistop_ticket=self
                )
                
                # Deduct amount from wallet
                return wallet.withdraw(self.total_fare)
            return False
        except Exception:
            return False
    
    def cancel_and_refund(self):
        """
        Cancel this ticket and process refund to user's wallet.
        """
        try:
            # Only process if ticket is in BOOKED status
            if self.status != 'BOOKED':
                return False
            
            # Check refund eligibility based on departure time
            hours_to_departure = (self.departure_time - timezone.now()).total_seconds() / 3600
            
            # Determine refund amount based on cancellation time
            if hours_to_departure >= 24:  # Full refund if >= 24 hours before departure
                refund_percentage = 1.0
            elif hours_to_departure >= 12:  # 75% refund if >= 12 hours before departure
                refund_percentage = 0.75
            elif hours_to_departure >= 6:  # 50% refund if >= 6 hours before departure
                refund_percentage = 0.5
            else:  # 25% refund if < 6 hours before departure
                refund_percentage = 0.25
            
            refund_amount = self.total_fare * refund_percentage
            
            # Process refund
            wallet = self.user.wallet
            wallet.deposit(refund_amount)
            
            # Create transaction record for the refund
            Transaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='REFUND',
                description=f"Refund for cancelled ticket #{self.id} - {self.bus.bus_number} ({int(refund_percentage*100)}%)",
                related_multistop_ticket=self
            )
            
            # Update bus available seats
            seat_count = self.passenger_count
            self.bus.available_seats += seat_count
            self.bus.save()
            
            # Mark ticket as cancelled
            self.status = 'CANCELLED'
            self.save()
            
            return True
        except Exception:
            return False
