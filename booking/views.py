from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.forms import formset_factory, modelformset_factory
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Q
from decimal import Decimal
from django.http import Http404

from .models import Bus, Ticket, Passenger, Wallet, Transaction, RouteSegment, RouteStop, MultiStopBus, MultiStopTicket
from .forms import PassengerForm, TicketBookingForm, BusSearchForm, WalletDepositForm, BusForm, PassengerEditForm

def index(request):
    """
    Homepage for the booking app displaying featured buses and search options.
    """
    # Get some featured buses (e.g., upcoming popular routes)
    featured_buses = Bus.objects.filter(
        is_active=True, 
        departure_time__gt=timezone.now()
    ).order_by('departure_time')[:5]
    
    # Initialize the search form
    search_form = BusSearchForm()
    
    context = {
        'featured_buses': featured_buses,
        'search_form': search_form,
    }
    return render(request, 'booking/index.html', context)


@login_required
def bus_detail(request, bus_id):
    """
    View to display detailed information about a specific bus.
    """
    bus = get_object_or_404(Bus, id=bus_id, is_active=True)
    
    # Check if the bus is fully booked
    is_fully_booked = bus.is_full
    
    # Get the total number of booked seats
    booked_seats_count = bus.capacity - bus.available_seats
    
    context = {
        'bus': bus,
        'is_fully_booked': is_fully_booked,
        'booked_seats_count': booked_seats_count,
    }
    return render(request, 'booking/bus_detail.html', context)


@login_required
def wallet_detail(request):
    """
    View to display wallet details and transaction history.
    """
    try:
        wallet = request.user.wallet
        transactions_list = wallet.transactions.all().order_by('-timestamp')
        
        # Pagination
        paginator = Paginator(transactions_list, 10)  # Show 10 transactions per page
        page = request.GET.get('page')
        transactions = paginator.get_page(page)
        
    except Wallet.DoesNotExist:
        # Create wallet if it doesn't exist (shouldn't happen due to signal, but just in case)
        wallet = Wallet.objects.create(user=request.user)
        transactions = []
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'booking/wallet_detail.html', context)


@login_required
def transaction_history(request):
    """
    View to display the transaction history for the user's wallet.
    """
    try:
        wallet = request.user.wallet
        transactions_list = wallet.transactions.all().order_by('-timestamp')
        
        # Filter by transaction type if specified
        transaction_type = request.GET.get('type')
        if transaction_type:
            transactions_list = transactions_list.filter(transaction_type=transaction_type)
        
        # Pagination
        paginator = Paginator(transactions_list, 15)  # Show 15 transactions per page
        page = request.GET.get('page')
        transactions = paginator.get_page(page)
        
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=request.user)
        transactions = []
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'transaction_type': transaction_type,
    }
    return render(request, 'booking/transaction_history.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_funds(request):
    """
    View for adding funds to the wallet.
    """
    if request.method == 'POST':
        # Get amount directly from POST data for simplicity
        try:
            amount = float(request.POST.get('amount', 0))
            if amount < 100:
                messages.error(request, _("Minimum deposit amount is ₹100."))
                return redirect('booking:add_money')
            
            # Convert to Decimal to avoid type mismatch
            decimal_amount = Decimal(str(amount))  # Convert via string for precision
            
            with transaction.atomic():    
                wallet = request.user.wallet
                success = wallet.deposit(decimal_amount, "Deposit to wallet")
                
                if success:
                    messages.success(request, _(f"Successfully added ₹{amount} to your wallet. Your new balance is ₹{wallet.balance}."))
                else:
                    messages.error(request, _("Failed to process deposit. Please try again."))
                    
            return redirect('booking:wallet_detail')
            
        except ValueError:
            messages.error(request, _("Please enter a valid amount."))
        except Wallet.DoesNotExist:
            # Create wallet if not exists
            wallet = Wallet.objects.create(user=request.user)
            messages.info(request, _("We've created a new wallet for you. Please try adding funds again."))
        except Exception as e:
            messages.error(request, _(f"An error occurred: {str(e)}"))
            
        return redirect('booking:wallet_detail')
    else:
        # Just render the simple form, no form instance needed
        return render(request, 'booking/add_funds.html')


@login_required
@require_http_methods(["GET", "POST"])
def bus_search(request):
    """
    View for searching buses by date and route.
    Includes both direct routes and multi-stop bus segments.
    """
    form = BusSearchForm(request.GET or None)
    buses = []
    multi_stop_buses = []
    
    if form.is_valid():
        source = form.cleaned_data.get('source')
        destination = form.cleaned_data.get('destination')
        date = form.cleaned_data.get('date')
        sort_by = request.GET.get('sort', 'departure_time')  # Default sort by departure time
        
        # Filter regular buses based on search criteria
        buses_query = Bus.objects.filter(is_active=True)
        
        if source:
            buses_query = buses_query.filter(route__origin__icontains=source)
        
        if destination:
            buses_query = buses_query.filter(route__destination__icontains=destination)
        
        if date:
            # Filter by departure date
            buses_query = buses_query.filter(departure_time__date=date)
        
        # Get regular buses
        buses = buses_query
        
        # Search for multi-stop buses with matching segments
        if source and destination:
            from django.db.models import F
            
            # Find multi-stop routes with matching segments
            multi_stop_buses_query = MultiStopBus.objects.filter(is_active=True)
            
            # Filter by date if provided
            if date:
                multi_stop_buses_query = multi_stop_buses_query.filter(departure_time__date=date)
            
            # Get all multi-stop buses
            potential_buses = list(multi_stop_buses_query)
            matching_multi_stop_buses = []
            
            # For each bus, check if it has a segment that matches the search
            for bus in potential_buses:
                # Get all stops for this route
                stops = bus.route.stops.all().order_by('sequence')
                
                # Check each combination of stops to see if any match the search
                for i, start_stop in enumerate(stops):
                    for end_stop in stops[i+1:]:  # Only consider stops after the start stop
                        # Check if this segment matches the search
                        if (source.lower() in start_stop.city.lower() and 
                            destination.lower() in end_stop.city.lower()):
                            # Add to matching buses with segment info
                            matching_multi_stop_buses.append({
                                'bus': bus,
                                'start_stop': start_stop,
                                'end_stop': end_stop
                            })
                            # Once we find a matching segment, break out of the inner loop
                            break
                    # If we found a match, no need to check other start stops
                    if matching_multi_stop_buses and matching_multi_stop_buses[-1]['bus'] == bus:
                        break
            
            multi_stop_buses = matching_multi_stop_buses
        
        # Apply sorting - note: this is simplified and may need adjustment
        # For proper sorting of combined results
        if sort_by == 'fare_low':
            buses = buses.order_by('fare')
            # For multi-stop buses, we'd need custom sorting based on segment fare
        elif sort_by == 'fare_high':
            buses = buses.order_by('-fare')
        elif sort_by == 'departure_early':
            buses = buses.order_by('departure_time')
        elif sort_by == 'departure_late':
            buses = buses.order_by('-departure_time')
        elif sort_by == 'duration':
            buses = buses.order_by('departure_time')
        else:
            buses = buses.order_by('departure_time')
    
    context = {
        'form': form,
        'buses': buses,
        'multi_stop_buses': multi_stop_buses,
        'search_performed': form.is_valid(),
        'current_sort': request.GET.get('sort', 'departure_time'),
    }
    return render(request, 'booking/bus_search.html', context)


@login_required
def view_seats(request, bus_id):
    """
    View to display available seats for a specific bus.
    Handles both regular buses and multi-stop buses.
    """
    # Check if this is a multi-stop bus
    try:
        bus = MultiStopBus.objects.get(id=bus_id, is_active=True)
        is_multi_stop = True
    except MultiStopBus.DoesNotExist:
        bus = get_object_or_404(Bus, id=bus_id, is_active=True)
        is_multi_stop = False
    
    # Get segment information if provided
    segment = None
    start_stop = None
    end_stop = None
    
    if is_multi_stop and 'segment' in request.GET:
        try:
            segment_params = request.GET.get('segment', '').split('-')
            if len(segment_params) == 2:
                start_stop_id, end_stop_id = segment_params
                start_stop = RouteStop.objects.get(id=start_stop_id, route=bus.route)
                end_stop = RouteStop.objects.get(id=end_stop_id, route=bus.route)
                
                # Try to get the segment
                segment = RouteSegment.objects.filter(
                    route=bus.route,
                    start_stop=start_stop,
                    end_stop=end_stop
                ).first()
        except (ValueError, RouteStop.DoesNotExist, RouteSegment.DoesNotExist):
            # If any error occurs, proceed without segment info
            pass
    
    # Get all booked seats for this bus
    if is_multi_stop:
        if segment:
            # Get tickets that overlap with the requested segment
            booked_tickets = MultiStopTicket.objects.filter(
                bus=bus, status='BOOKED'
            ).filter(
                # Find tickets where the journey overlaps with the requested segment
                Q(start_stop__sequence__lte=end_stop.sequence) & 
                Q(end_stop__sequence__gte=start_stop.sequence)
            )
        else:
            # Without segment info, show all booked tickets for this bus
            booked_tickets = MultiStopTicket.objects.filter(bus=bus, status='BOOKED')
    else:
        # Regular buses
        booked_tickets = Ticket.objects.filter(bus=bus, status='BOOKED')
    
    # Extract booked seat numbers
    booked_seats = []
    for ticket in booked_tickets:
        # Assuming seat_numbers is a comma-separated string
        seats = [seat.strip() for seat in ticket.seat_numbers.split(',')]
        booked_seats.extend(seats)
    
    # Generate all seat numbers (assuming 40 seats per bus in a 10x4 layout)
    total_seats = bus.total_seats
    all_seats = []
    
    for i in range(1, total_seats + 1):
        seat_num = str(i)
        all_seats.append({
            'number': seat_num,
            'is_booked': seat_num in booked_seats
        })
    
    context = {
        'bus': bus,
        'is_multi_stop': is_multi_stop,
        'segment': segment,
        'start_stop': start_stop,
        'end_stop': end_stop,
        'seats': all_seats,
        'booked_seats': booked_seats,
        'wallet_balance': request.user.wallet.balance,
    }
    return render(request, 'booking/view_seats.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def book_ticket(request, bus_id):
    """
    View for booking a ticket using wallet balance.
    First step of booking that collects seat class and numbers.
    Handles both regular buses and multi-stop buses.
    Uses logged-in user's details automatically instead of collecting passenger information.
    """
    # Check if this is a multi-stop bus
    try:
        bus = MultiStopBus.objects.get(id=bus_id, is_active=True)
        is_multi_stop = True
    except MultiStopBus.DoesNotExist:
        bus = get_object_or_404(Bus, id=bus_id, is_active=True)
        is_multi_stop = False
    
    if bus.is_full:
        messages.error(request, _("Sorry, this bus is fully booked."))
        return redirect('booking:bus_search')
    
    # Get segment information if this is a multi-stop bus
    segment = None
    start_stop = None
    end_stop = None
    
    if is_multi_stop and 'segment' in request.GET:
        try:
            segment_params = request.GET.get('segment', '').split('-')
            if len(segment_params) == 2:
                start_stop_id, end_stop_id = segment_params
                start_stop = RouteStop.objects.get(id=start_stop_id, route=bus.route)
                end_stop = RouteStop.objects.get(id=end_stop_id, route=bus.route)
                
                # Try to get the segment
                segment = RouteSegment.objects.filter(
                    route=bus.route,
                    start_stop=start_stop,
                    end_stop=end_stop
                ).first()
        except (ValueError, RouteStop.DoesNotExist, RouteSegment.DoesNotExist):
            # If any error occurs, proceed without segment info
            pass
    
    if request.method == 'POST':
        booking_form = TicketBookingForm(request.POST, bus=bus)
        
        if booking_form.is_valid():
            # Get selected segment if provided in the form
            form_segment = booking_form.cleaned_data.get('segment')
            if form_segment:
                segment = form_segment
                start_stop = segment.start_stop
                end_stop = segment.end_stop
            
            # For multi-stop buses, ensure we have segment info
            if is_multi_stop and not (segment and start_stop and end_stop):
                messages.error(request, _("Please select a valid journey segment."))
                return redirect('booking:book_ticket', bus_id=bus.id)
            
            # Get selected seat class and calculate fare
            seat_class = booking_form.cleaned_data.get('seat_class')
            
            # Get fare based on seat class and segment
            if is_multi_stop and segment:
                fare_per_seat = bus.calculate_segment_fare(segment, seat_class)
            else:
                # Regular bus fare
                fare_per_seat = bus.get_fare_for_class(seat_class)
            
            # Validate seat numbers
            selected_seats = booking_form.cleaned_data.get('seat_numbers', '').split(',')
            selected_seats = [s.strip() for s in selected_seats if s.strip()]
            seat_count = len(selected_seats)
            
            if seat_count == 0:
                messages.error(request, _("Please select at least one seat."))
                return redirect('booking:book_ticket', bus_id=bus.id)
                
            # Check segment availability for multi-stop buses
            if is_multi_stop and segment:
                # Check segment availability
                available_seats = bus.get_segment_availability(segment)
                if seat_count > available_seats:
                    messages.error(request, _("Not enough seats available for this segment."))
                    return redirect('booking:book_ticket', bus_id=bus.id)
            
            total_fare = fare_per_seat * seat_count
            
            # Check if user has enough balance
            try:
                wallet = request.user.wallet
                if not wallet.has_sufficient_balance(total_fare):
                    messages.error(
                        request, 
                        _(f"Insufficient balance. You need ₹{total_fare} but have only ₹{wallet.balance}.")
                    )
                    return redirect('booking:wallet_detail')
                
                # Get user profile information for passenger details
                user = request.user
                
                # Create a single passenger record with the user's information
                passenger_data = {
                    'name': f"{user.first_name} {user.last_name}".strip() or user.email,
                    'age': 30,  # Default age
                    'gender': 'M',  # Default gender
                    'phone': user.profile.phone if hasattr(user, 'profile') and hasattr(user.profile, 'phone') else '',
                    'id_number': user.profile.id_number if hasattr(user, 'profile') and hasattr(user.profile, 'id_number') else ''
                }
                
                # Store booking data in session for OTP verification - still storing this for compatibility
                booking_data = {
                    'bus_id': bus.id,
                    'is_multi_stop': is_multi_stop,
                    'segment_id': segment.id if segment else None,
                    'start_stop_id': start_stop.id if start_stop else None,
                    'end_stop_id': end_stop.id if end_stop else None,
                    'seat_class': seat_class,
                    'seat_numbers': booking_form.cleaned_data.get('seat_numbers'),
                    'total_fare': str(total_fare),  # Convert Decimal to string for session storage
                    'passenger_data': [passenger_data for _ in range(seat_count)]
                }
                request.session['booking_data'] = booking_data
                
                # BYPASSING OTP - Direct booking processing
                try:
                    with transaction.atomic():
                        # Create passengers first
                        passengers = []
                        for passenger_data in booking_data['passenger_data']:
                            passenger = Passenger.objects.create(**passenger_data)
                            passengers.append(passenger)
                        
                        # Create the appropriate ticket type based on bus type
                        if is_multi_stop:
                            # For multi-stop buses, we must have segment data
                            if not (segment and start_stop and end_stop):
                                raise Exception(_("Segment information is missing for multi-stop booking."))
                            
                            # Create multi-stop ticket
                            ticket = MultiStopTicket.objects.create(
                                user=request.user,
                                bus=bus,
                                start_stop=start_stop,
                                end_stop=end_stop,
                                total_fare=Decimal(booking_data['total_fare']),
                                seat_numbers=booking_data['seat_numbers'],
                                seat_class=booking_data.get('seat_class', 'GENERAL'),
                                status='BOOKED'
                            )
                        else:
                            # Create regular ticket
                            ticket_data = {
                                'user': request.user,
                                'bus': bus,
                                'total_fare': Decimal(booking_data['total_fare']),
                                'seat_numbers': booking_data['seat_numbers'],
                                'seat_class': booking_data.get('seat_class', 'GENERAL'),
                                'status': 'BOOKED'
                            }
                            
                            # Add segment data if available
                            if segment and start_stop and end_stop:
                                ticket_data.update({
                                    'start_stop': start_stop,
                                    'end_stop': end_stop
                                })
                            
                            ticket = Ticket.objects.create(**ticket_data)
                        
                        # Add passengers to ticket
                        for passenger in passengers:
                            ticket.passengers.add(passenger)
                        
                        # Book with wallet (deduct money)
                        if is_multi_stop:
                            if not ticket.book_with_wallet():
                                # If booking with wallet fails, rollback
                                raise Exception(_("Failed to process payment."))
                        else:
                            if not ticket.book_with_wallet():
                                # If booking with wallet fails, rollback
                                raise Exception(_("Failed to process payment."))
                        
                        # Update available seats
                        seat_count = len(booking_data['passenger_data'])
                        # Note: We're reducing the bus's available seats count 
                        # even though for multi-stop buses this isn't the full picture
                        bus.available_seats -= seat_count
                        bus.save()
                        
                        # Clear session data
                        if 'booking_data' in request.session:
                            del request.session['booking_data']
                        
                        messages.success(request, _(f"Ticket booked successfully! Ticket ID: #{ticket.id}"))
                        return redirect('booking:booking_success', ticket_id=ticket.id)
                except Exception as e:
                    messages.error(request, str(e))
                    return redirect('booking:book_ticket', bus_id=bus.id)
            
            except Wallet.DoesNotExist:
                messages.error(request, _("Wallet not found. Please contact support."))
                return redirect('booking:wallet_detail')
            except Exception as e:
                messages.error(request, str(e))
                return redirect('booking:book_ticket', bus_id=bus.id)
    else:
        booking_form = TicketBookingForm(bus=bus)
    
    # Calculate fare estimate
    fare_estimate = bus.fare
    if is_multi_stop and segment:
        fare_estimate = bus.calculate_segment_fare(segment, 'GENERAL')
    
    context = {
        'bus': bus,
        'is_multi_stop': is_multi_stop,
        'segment': segment,
        'start_stop': start_stop,
        'end_stop': end_stop,
        'booking_form': booking_form,
        'wallet_balance': request.user.wallet.balance,
        'total_fare_estimate': fare_estimate,
    }
    return render(request, 'booking/ticket_booking.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def verify_booking_otp(request):
    """
    View for verifying OTP during ticket booking.
    Handles both regular and multi-stop ticket creation.
    """
    # Check if booking data exists in session
    if 'booking_data' not in request.session:
        messages.error(request, _("Booking session expired. Please start again."))
        return redirect('booking:bus_search')
    
    booking_data = request.session['booking_data']
    is_multi_stop = booking_data.get('is_multi_stop', False)
    
    # Get the appropriate bus based on bus type
    if is_multi_stop:
        bus = get_object_or_404(MultiStopBus, id=booking_data['bus_id'], is_active=True)
    else:
        bus = get_object_or_404(Bus, id=booking_data['bus_id'], is_active=True)
    
    # Get segment data if it exists
    segment = None
    start_stop = None
    end_stop = None
    
    if booking_data.get('segment_id'):
        segment = get_object_or_404(RouteSegment, id=booking_data['segment_id'])
        start_stop = get_object_or_404(RouteStop, id=booking_data['start_stop_id'])
        end_stop = get_object_or_404(RouteStop, id=booking_data['end_stop_id'])
    
    # Process form submission
    if request.method == 'POST':
        from accounts.forms import OTPVerificationForm
        form = OTPVerificationForm(
            request.POST, 
            email=request.user.email, 
            action='BOOKING'
        )
        
        if form.is_valid():
            # OTP is valid, process the ticket booking
            try:
                with transaction.atomic():
                    # Create passengers first
                    passengers = []
                    for passenger_data in booking_data['passenger_data']:
                        passenger = Passenger.objects.create(**passenger_data)
                        passengers.append(passenger)
                    
                    # Create the appropriate ticket type based on bus type
                    if is_multi_stop:
                        # For multi-stop buses, we must have segment data
                        if not (segment and start_stop and end_stop):
                            raise Exception(_("Segment information is missing for multi-stop booking."))
                        
                        # Create multi-stop ticket
                        ticket = MultiStopTicket.objects.create(
                            user=request.user,
                            bus=bus,
                            start_stop=start_stop,
                            end_stop=end_stop,
                            total_fare=Decimal(booking_data['total_fare']),
                            seat_numbers=booking_data['seat_numbers'],
                            seat_class=booking_data.get('seat_class', 'GENERAL'),
                            status='BOOKED'
                        )
                    else:
                        # Create regular ticket
                        ticket_data = {
                            'user': request.user,
                            'bus': bus,
                            'total_fare': Decimal(booking_data['total_fare']),
                            'seat_numbers': booking_data['seat_numbers'],
                            'seat_class': booking_data.get('seat_class', 'GENERAL'),
                            'status': 'BOOKED'
                        }
                        
                        # Add segment data if available
                        if segment and start_stop and end_stop:
                            ticket_data.update({
                                'start_stop': start_stop,
                                'end_stop': end_stop
                            })
                        
                        ticket = Ticket.objects.create(**ticket_data)
                    
                    # Add passengers to ticket
                    for passenger in passengers:
                        ticket.passengers.add(passenger)
                    
                    # Book with wallet (deduct money)
                    if is_multi_stop:
                        if not ticket.book_with_wallet():
                            # If booking with wallet fails, rollback
                            raise Exception(_("Failed to process payment."))
                    else:
                        if not ticket.book_with_wallet():
                            # If booking with wallet fails, rollback
                            raise Exception(_("Failed to process payment."))
                    
                    # Update available seats
                    seat_count = len(booking_data['passenger_data'])
                    # Note: We're reducing the bus's available seats count 
                    # even though for multi-stop buses this isn't the full picture
                    bus.available_seats -= seat_count
                    bus.save()
                    
                    # Clear session data
                    if 'booking_data' in request.session:
                        del request.session['booking_data']
                    
                    messages.success(request, _(f"Ticket booked successfully! Ticket ID: #{ticket.id}"))
                    return redirect('booking:booking_success', ticket_id=ticket.id)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('booking:verify_booking_otp')
    else:
        from accounts.forms import OTPVerificationForm
        form = OTPVerificationForm()
    
    # Get seat class display name for context
    seat_class_display = dict(Bus.SEAT_CLASS_CHOICES).get(booking_data.get('seat_class', 'GENERAL'), 'General')
    
    # Calculate departure and arrival times 
    departure_time = bus.departure_time
    arrival_time = bus.arrival_time
    
    if segment and start_stop and end_stop:
        # If we have segment info, calculate segment-specific times
        departure_time = start_stop.get_departure_time(bus.departure_time) or bus.departure_time
        arrival_time = end_stop.get_arrival_time(bus.departure_time) or bus.arrival_time
    
    context = {
        'form': form,
        'email': request.user.email,
        'action': 'Booking',
        'bus': bus,
        'segment': segment,
        'start_stop': start_stop,
        'end_stop': end_stop,
        'departure_time': departure_time,
        'arrival_time': arrival_time,
        'total_fare': booking_data['total_fare'],
        'seat_count': len(booking_data['passenger_data']),
        'seat_class': seat_class_display,
        'is_multi_stop': is_multi_stop,
        'resend_url': reverse('booking:resend_booking_otp'),
    }
    return render(request, 'booking/verify_booking_otp.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def resend_booking_otp(request):
    """
    View for resending OTP for booking verification.
    """
    if 'booking_data' not in request.session:
        messages.error(request, _("Booking session expired. Please start again."))
        return redirect('booking:bus_search')
    
    booking_data = request.session['booking_data']
    
    if request.method == 'POST':
        from .utils import send_booking_otp
        if send_booking_otp(request.user, booking_data['bus_id'], booking_data):
            messages.success(request, _("A new verification code has been sent to your email."))
        else:
            messages.error(request, _("Failed to send verification code. Please try again."))
        
        return redirect('booking:verify_booking_otp')
    
    # GET request
    context = {
        'email': request.user.email,
        'action': 'Booking'
    }
    return render(request, 'accounts/resend_otp.html', context)


@login_required
def booking_success(request, ticket_id):
    """
    View to display booking success page after ticket purchase.
    Handles both regular and multi-stop tickets.
    """
    # Try to find the ticket in different models
    ticket = None
    is_multi_stop = False
    
    try:
        ticket = Ticket.objects.get(id=ticket_id, user=request.user)
    except Ticket.DoesNotExist:
        try:
            ticket = MultiStopTicket.objects.get(id=ticket_id, user=request.user)
            is_multi_stop = True
        except MultiStopTicket.DoesNotExist:
            # If ticket not found in either model, return 404
            raise Http404("Ticket not found")
    
    context = {
        'ticket': ticket,
        'passengers': ticket.passengers.all(),
        'is_multi_stop': is_multi_stop,
    }
    
    return render(request, 'booking/booking_success.html', context)


@login_required
def ticket_detail(request, ticket_id):
    """
    View to display ticket details.
    Handles both regular and multi-stop tickets.
    """
    # Try to find the ticket in different models
    ticket = None
    is_multi_stop = False
    
    try:
        ticket = Ticket.objects.get(id=ticket_id, user=request.user)
    except Ticket.DoesNotExist:
        try:
            ticket = MultiStopTicket.objects.get(id=ticket_id, user=request.user)
            is_multi_stop = True
        except MultiStopTicket.DoesNotExist:
            # If ticket not found in either model, return 404
            raise Http404("Ticket not found")
    
    # Check if ticket can be cancelled (6 hours before departure)
    can_cancel = False
    if ticket.status == 'BOOKED':
        if is_multi_stop:
            # For multi-stop tickets, use the departure_time property
            time_until_departure = ticket.departure_time - timezone.now()
        else:
            # For regular tickets, use the bus departure time
            time_until_departure = ticket.bus.departure_time - timezone.now()
        
        can_cancel = time_until_departure > timedelta(hours=6)
    
    context = {
        'ticket': ticket,
        'passengers': ticket.passengers.all(),
        'can_cancel': can_cancel,
        'now': timezone.now(),
        'is_multi_stop': is_multi_stop,
    }
    return render(request, 'booking/ticket_detail.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_ticket(request, ticket_id):
    """
    View to cancel a ticket and refund the wallet.
    Handles both regular and multi-stop tickets.
    """
    # Try to find the ticket in different models
    ticket = None
    is_multi_stop = False
    
    try:
        ticket = Ticket.objects.get(id=ticket_id, user=request.user)
    except Ticket.DoesNotExist:
        try:
            ticket = MultiStopTicket.objects.get(id=ticket_id, user=request.user)
            is_multi_stop = True
        except MultiStopTicket.DoesNotExist:
            # If ticket not found in either model, return 404
            raise Http404("Ticket not found")
    
    if ticket.status != 'BOOKED':
        messages.error(request, _("This ticket cannot be cancelled."))
        return redirect('booking:ticket_detail', ticket_id=ticket.id)
    
    # Check if ticket can be cancelled (6 hours before departure)
    if is_multi_stop:
        # For multi-stop tickets, use the departure_time property
        time_until_departure = ticket.departure_time - timezone.now()
    else:
        # For regular tickets, use the bus departure time
        time_until_departure = ticket.bus.departure_time - timezone.now()
    
    if time_until_departure <= timedelta(hours=6):
        messages.error(request, _("Tickets can only be cancelled at least 6 hours before departure."))
        return redirect('booking:ticket_detail', ticket_id=ticket.id)
    
    # Cancel ticket (which also processes refund to wallet)
    if ticket.cancel():
        messages.success(
            request, 
            _(f"Ticket #{ticket.id} cancelled successfully. ₹{ticket.total_fare} has been refunded to your wallet.")
        )
    else:
        messages.error(request, _("Failed to cancel ticket."))
    
    return redirect('booking:ticket_detail', ticket_id=ticket.id)


@login_required
def confirm_booking(request, booking_id):
    """
    View to confirm a booking before final payment.
    """
    # For simplicity, we'll redirect to the ticket detail view since we don't have a separate booking confirmation process
    # In a real system, this might show a summary and confirmation page before finalizing payment
    return redirect('booking:ticket_detail', ticket_id=booking_id)


@login_required
def user_tickets(request):
    """
    View to display all tickets booked by user.
    """
    tickets = Ticket.objects.filter(user=request.user).order_by('-booking_time')
    
    context = {
        'tickets': tickets,
    }
    return render(request, 'booking/user_tickets.html', context)


@login_required
def user_journeys(request):
    """
    View to display upcoming and past journeys for the user.
    Includes both regular and multi-stop tickets.
    """
    now = timezone.now()
    
    # Create empty lists to store combined tickets
    upcoming_tickets = []
    past_tickets = []
    
    # Get regular tickets for the user
    regular_tickets = Ticket.objects.filter(user=request.user).select_related('bus')
    
    # Split regular tickets into upcoming and past journeys
    for ticket in regular_tickets:
        ticket.is_multi_stop = False  # Flag to identify ticket type in template
        if ticket.status == 'BOOKED' and ticket.bus.departure_time > now:
            upcoming_tickets.append(ticket)
        else:
            past_tickets.append(ticket)
    
    # Get multi-stop tickets for the user
    multi_stop_tickets = MultiStopTicket.objects.filter(user=request.user).select_related('bus')
    
    # Split multi-stop tickets into upcoming and past journeys
    for ticket in multi_stop_tickets:
        ticket.is_multi_stop = True  # Flag to identify ticket type in template
        if ticket.status == 'BOOKED' and ticket.departure_time > now:
            upcoming_tickets.append(ticket)
        else:
            past_tickets.append(ticket)
    
    # Sort the combined lists
    upcoming_tickets.sort(key=lambda ticket: ticket.bus.departure_time if not getattr(ticket, 'is_multi_stop', False) 
                          else ticket.departure_time)
    past_tickets.sort(key=lambda ticket: ticket.bus.departure_time if not getattr(ticket, 'is_multi_stop', False) 
                      else ticket.departure_time, reverse=True)
    
    # Apply filters if provided
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'upcoming':
        past_tickets = []
    elif filter_type == 'past':
        upcoming_tickets = []
    
    context = {
        'upcoming_tickets': upcoming_tickets,
        'past_tickets': past_tickets,
        'filter_type': filter_type,
    }
    return render(request, 'booking/user_journeys.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def edit_passenger(request, ticket_id, passenger_id):
    """
    View to edit passenger information for an existing booking.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    passenger = get_object_or_404(Passenger, id=passenger_id, ticket=ticket)
    
    # Check if ticket is still editable (not departed or cancelled)
    if ticket.status != 'BOOKED' or ticket.bus.departure_time <= timezone.now():
        messages.error(request, _("This ticket can no longer be edited."))
        return redirect('booking:ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        form = PassengerEditForm(request.POST, instance=passenger)
        if form.is_valid():
            form.save()
            messages.success(request, _("Passenger information updated successfully."))
            return redirect('booking:ticket_detail', ticket_id=ticket.id)
    else:
        form = PassengerEditForm(instance=passenger)
    
    context = {
        'form': form,
        'ticket': ticket,
        'passenger': passenger,
    }
    return render(request, 'booking/edit_passenger.html', context)


@login_required
@require_http_methods(["GET"])
def get_passenger_details(request, ticket_id):
    """
    AJAX view to get passenger details for a ticket.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Check if the user is authorized (either the ticket owner or an admin)
    if not (request.user.is_staff or request.user == ticket.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    passengers = []
    for passenger in ticket.passengers.all():
        passengers.append({
            'id': passenger.id,
            'name': passenger.name,
            'age': passenger.age,
            'gender': passenger.get_gender_display(),
            'id_number': passenger.id_number,
            'phone': passenger.phone,
        })
    
    return JsonResponse({'passengers': passengers})


# Admin Views
@staff_member_required
def admin_bus_list(request):
    """
    Admin view to list all buses.
    """
    buses = Bus.objects.all().order_by('-departure_time')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        buses = buses.filter(is_active=True)
    elif status_filter == 'inactive':
        buses = buses.filter(is_active=False)
    
    context = {
        'buses': buses,
        'status_filter': status_filter,
    }
    return render(request, 'admin/booking/bus_list.html', context)


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_bus_create(request):
    """
    Admin view to create a new bus.
    """
    if request.method == 'POST':
        form = BusForm(request.POST)
        if form.is_valid():
            bus = form.save()
            messages.success(request, _(f"Bus {bus.bus_number} created successfully."))
            return redirect('booking:admin_bus_list')
    else:
        form = BusForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'admin/booking/bus_form.html', context)


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_bus_edit(request, bus_id):
    """
    Admin view to edit a bus.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    
    if request.method == 'POST':
        form = BusForm(request.POST, instance=bus)
        if form.is_valid():
            bus = form.save()
            messages.success(request, _(f"Bus {bus.bus_number} updated successfully."))
            return redirect('booking:admin_bus_list')
    else:
        form = BusForm(instance=bus)
    
    context = {
        'form': form,
        'bus': bus,
        'action': 'Edit',
    }
    return render(request, 'admin/booking/bus_form.html', context)


@staff_member_required
@require_http_methods(["POST"])
def admin_bus_cancel(request, bus_id):
    """
    Admin view to cancel a bus and refund all bookings.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    
    if not bus.is_active:
        messages.error(request, _("This bus is already cancelled."))
        return redirect('booking:admin_bus_list')
    
    # Get all active tickets for this bus
    active_tickets = Ticket.objects.filter(bus=bus, status='BOOKED')
    refund_count = 0
    
    try:
        with transaction.atomic():
            # Cancel the bus first
            bus.is_active = False
            bus.save()
            
            # Process refunds for all active tickets
            for ticket in active_tickets:
                if ticket.cancel(admin_cancelled=True):
                    refund_count += 1
            
            messages.success(
                request,
                _(f"Bus {bus.bus_number} cancelled successfully. {refund_count} tickets refunded.")
            )
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('booking:admin_bus_list')


@staff_member_required
def admin_bus_bookings(request, bus_id):
    """
    Admin view to see all bookings for a specific bus.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    tickets = Ticket.objects.filter(bus=bus).order_by('-booking_time')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    context = {
        'bus': bus,
        'tickets': tickets,
        'status_filter': status_filter,
        'total_tickets': tickets.count(),
        'booked_tickets': tickets.filter(status='BOOKED').count(),
        'cancelled_tickets': tickets.filter(status='CANCELLED').count(),
        'total_revenue': sum(ticket.total_fare for ticket in tickets.filter(status='BOOKED')),
    }
    return render(request, 'admin/booking/bus_bookings.html', context)
