from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
import xlsxwriter
import io
from datetime import datetime

from .models import Route, RouteStop, RouteSegment, Bus, Passenger, Ticket, Wallet, Transaction, MultiStopBus, MultiStopTicket, MultiStopRoute


class RouteStopInline(admin.TabularInline):
    """
    Inline admin for RouteStop model within MultiStopRoute admin.
    """
    model = RouteStop
    extra = 1
    ordering = ('sequence',)


class RouteSegmentInline(admin.TabularInline):
    """
    Inline admin for RouteSegment model within MultiStopRoute admin.
    """
    model = RouteSegment
    extra = 1
    fields = ('start_stop', 'end_stop', 'distance', 'duration', 'base_fare_multiplier')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """
    Admin interface for Route model.
    """
    list_display = ('origin', 'destination', 'distance', 'estimated_duration')
    search_fields = ('origin', 'destination')
    ordering = ('origin', 'destination')
    
    fieldsets = (
        (None, {
            'fields': ('origin', 'destination')
        }),
        (_('Details'), {
            'fields': ('distance', 'estimated_duration')
        }),
    )


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    """
    Admin interface for RouteStop model.
    """
    list_display = ('route', 'city', 'sequence', 'arrival_offset', 'departure_offset', 
                   'is_boarding_point', 'is_dropping_point')
    list_filter = ('route', 'is_boarding_point', 'is_dropping_point')
    search_fields = ('city', 'route__name')
    ordering = ('route', 'sequence')


@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin):
    """
    Admin interface for RouteSegment model.
    """
    list_display = ('route', 'start_stop', 'end_stop', 'distance', 'duration', 'base_fare_multiplier')
    list_filter = ('route',)
    search_fields = ('route__name', 'start_stop__city', 'end_stop__city')
    ordering = ('route', 'start_stop__sequence')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    """
    Admin interface for Bus model.
    """
    list_display = ('bus_number', 'route', 'departure_time', 'arrival_time', 
                    'total_seats', 'available_seats', 'fare', 'is_active')
    list_filter = ('route', 'departure_time', 'is_active')
    search_fields = ('bus_number', 'route__name')
    date_hierarchy = 'departure_time'
    list_editable = ('fare', 'is_active')
    readonly_fields = ('seats_taken',)
    
    fieldsets = (
        (None, {
            'fields': ('bus_number', 'route', 'is_active')
        }),
        (_('Schedule'), {
            'fields': ('departure_time', 'arrival_time')
        }),
        (_('Seating & Capacity'), {
            'fields': ('total_seats', 'available_seats')
        }),
        (_('Fare Information'), {
            'fields': ('fare', 'sleeper_fare', 'luxury_fare', 
                     'has_general_seats', 'has_sleeper_seats', 'has_luxury_seats')
        }),
    )

    actions = ['export_bookings_to_excel']

    def export_bookings_to_excel(self, request, queryset):
        """
        Export all bookings for selected buses to Excel.
        """
        # Create a file-like buffer to receive Excel data
        output = io.BytesIO()
        
        # Create workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        
        # Add a bold format for headers
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        
        for bus in queryset:
            # Create worksheet for each bus
            worksheet = workbook.add_worksheet(f"Bus {bus.bus_number[:15]}")
            
            # Write header row
            headers = [
                'Ticket ID', 
                'Booking Time', 
                'User Email', 
                'Passenger Name', 
                'Passenger Age', 
                'Passenger Gender',
                'Passenger ID', 
                'Passenger Phone', 
                'Seat Numbers', 
                'Seat Class', 
                'Total Fare', 
                'Status'
            ]
            
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # Get all tickets for this bus
            tickets = Ticket.objects.filter(bus=bus)
            
            # Data rows
            row_num = 1
            for ticket in tickets:
                for passenger in ticket.passengers.all():
                    worksheet.write(row_num, 0, f"#{ticket.id}")
                    worksheet.write_datetime(row_num, 1, ticket.booking_time, date_format)
                    worksheet.write(row_num, 2, ticket.user.email)
                    worksheet.write(row_num, 3, passenger.name)
                    worksheet.write(row_num, 4, passenger.age)
                    worksheet.write(row_num, 5, passenger.get_gender_display())
                    worksheet.write(row_num, 6, passenger.id_number or 'N/A')
                    worksheet.write(row_num, 7, passenger.phone or 'N/A')
                    worksheet.write(row_num, 8, ticket.seat_numbers)
                    worksheet.write(row_num, 9, ticket.get_seat_class_display())
                    worksheet.write(row_num, 10, float(ticket.total_fare))
                    worksheet.write(row_num, 11, ticket.get_status_display())
                    row_num += 1
            
            # Auto-adjust columns' width
            for col_num, _ in enumerate(headers):
                worksheet.set_column(col_num, col_num, 15)
        
        workbook.close()
        
        # Set up response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="bus_bookings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
    
    export_bookings_to_excel.short_description = _("Export bookings to Excel")


class PassengerInline(admin.TabularInline):
    """
    Inline admin for Passenger model within Ticket admin.
    """
    model = Ticket.passengers.through
    extra = 1


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    """
    Admin interface for Passenger model.
    """
    list_display = ('name', 'age', 'gender', 'phone')
    list_filter = ('gender', 'age')
    search_fields = ('name', 'id_number', 'phone')


class TransactionInline(admin.TabularInline):
    """
    Inline admin for Transaction model within Wallet admin.
    """
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'description', 'timestamp', 'related_ticket')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """
    Admin interface for Wallet model.
    """
    list_display = ('user', 'balance', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TransactionInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'balance')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['add_funds']
    
    def add_funds(self, request, queryset):
        """Add 500 to each selected wallet for testing"""
        for wallet in queryset:
            wallet.deposit(500)
        self.message_user(request, _("Added ₹500 to each selected wallet."))
    add_funds.short_description = _("Add ₹500 to selected wallets")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for Transaction model.
    """
    list_display = ('wallet', 'transaction_type', 'amount', 'timestamp', 'related_ticket')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('wallet__user__email', 'description')
    date_hierarchy = 'timestamp'
    readonly_fields = ('wallet', 'transaction_type', 'amount', 'description', 'timestamp', 'related_ticket')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    fieldsets = (
        (None, {
            'fields': ('wallet', 'transaction_type', 'amount')
        }),
        (_('Details'), {
            'fields': ('description', 'timestamp', 'related_ticket')
        }),
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Admin interface for Ticket model.
    """
    list_display = ('id', 'user', 'bus', 'booking_time', 
                  'status', 'seat_class', 'total_fare', 'passenger_count')
    list_filter = ('status', 'booking_time', 'bus__route', 'seat_class')
    search_fields = ('user__email', 'user__full_name', 'bus__bus_number')
    date_hierarchy = 'booking_time'
    readonly_fields = ('booking_time', 'passenger_count')
    inlines = [PassengerInline]
    exclude = ('passengers',)
    
    actions = ['mark_as_cancelled', 'mark_as_completed']
    
    def mark_as_cancelled(self, request, queryset):
        for ticket in queryset.filter(status='BOOKED'):
            ticket.cancel()
        self.message_user(request, _("Selected tickets have been cancelled."))
    mark_as_cancelled.short_description = _("Mark selected tickets as cancelled")
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='BOOKED').update(status='COMPLETED')
        self.message_user(request, _("%s tickets have been marked as completed.") % updated)
    mark_as_completed.short_description = _("Mark selected tickets as completed")
    
    def passenger_count(self, obj):
        return obj.passengers.count()
    passenger_count.short_description = _("Number of passengers")


@admin.register(MultiStopBus)
class MultiStopBusAdmin(admin.ModelAdmin):
    """
    Admin interface for MultiStopBus model.
    """
    list_display = ('bus_number', 'route', 'departure_time', 'arrival_time', 
                    'total_seats', 'available_seats', 'fare', 'is_active')
    list_filter = ('route', 'departure_time', 'is_active')
    search_fields = ('bus_number', 'route__name')
    date_hierarchy = 'departure_time'
    list_editable = ('fare', 'is_active')
    
    actions = ['export_bookings_to_excel']
    
    def export_bookings_to_excel(self, request, queryset):
        """
        Export all bookings for selected multi-stop buses to Excel.
        """
        # Create a file-like buffer to receive Excel data
        output = io.BytesIO()
        
        # Create workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output)
        
        # Add a bold format for headers
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        
        for bus in queryset:
            # Create worksheet for each bus
            worksheet = workbook.add_worksheet(f"Bus {bus.bus_number[:15]}")
            
            # Write header row
            headers = [
                'Ticket ID', 
                'Booking Time', 
                'User Email', 
                'From', 
                'To', 
                'Passenger Name', 
                'Passenger Age', 
                'Passenger Gender',
                'Passenger ID', 
                'Passenger Phone', 
                'Seat Numbers', 
                'Seat Class', 
                'Total Fare', 
                'Status'
            ]
            
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # Get all tickets for this bus
            tickets = MultiStopTicket.objects.filter(bus=bus)
            
            # Data rows
            row_num = 1
            for ticket in tickets:
                for passenger in ticket.passengers.all():
                    worksheet.write(row_num, 0, f"#{ticket.id}")
                    worksheet.write_datetime(row_num, 1, ticket.booking_time, date_format)
                    worksheet.write(row_num, 2, ticket.user.email)
                    worksheet.write(row_num, 3, ticket.start_stop.city)
                    worksheet.write(row_num, 4, ticket.end_stop.city)
                    worksheet.write(row_num, 5, passenger.name)
                    worksheet.write(row_num, 6, passenger.age)
                    worksheet.write(row_num, 7, passenger.get_gender_display())
                    worksheet.write(row_num, 8, passenger.id_number or 'N/A')
                    worksheet.write(row_num, 9, passenger.phone or 'N/A')
                    worksheet.write(row_num, 10, ticket.seat_numbers)
                    worksheet.write(row_num, 11, ticket.get_seat_class_display())
                    worksheet.write(row_num, 12, float(ticket.total_fare))
                    worksheet.write(row_num, 13, ticket.get_status_display())
                    row_num += 1
            
            # Auto-adjust columns' width
            for col_num, _ in enumerate(headers):
                worksheet.set_column(col_num, col_num, 15)
        
        workbook.close()
        
        # Set up response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="multistop_bus_bookings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
    
    export_bookings_to_excel.short_description = _("Export bookings to Excel")


@admin.register(MultiStopRoute)
class MultiStopRouteAdmin(admin.ModelAdmin):
    """
    Admin interface for MultiStopRoute model.
    """
    list_display = ('name', 'description', 'is_active', 'get_stop_count', 'get_first_stop', 'get_last_stop')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    inlines = [RouteStopInline, RouteSegmentInline]
    
    def get_stop_count(self, obj):
        return obj.stops.count()
    get_stop_count.short_description = _("Stops")
    
    def get_first_stop(self, obj):
        stops = obj.get_stops_ordered()
        return stops.first().city if stops.exists() else "-"
    get_first_stop.short_description = _("First Stop")
    
    def get_last_stop(self, obj):
        stops = obj.get_stops_ordered()
        return stops.last().city if stops.exists() else "-"
    get_last_stop.short_description = _("Last Stop")


class MultiStopPassengerInline(admin.TabularInline):
    """
    Inline admin for Passenger model within MultiStopTicket admin.
    """
    model = MultiStopTicket.passengers.through
    extra = 1


@admin.register(MultiStopTicket)
class MultiStopTicketAdmin(admin.ModelAdmin):
    """
    Admin interface for MultiStopTicket model.
    """
    list_display = ('id', 'user', 'bus', 'start_stop', 'end_stop', 'booking_time', 
                  'status', 'seat_class', 'total_fare', 'passenger_count')
    list_filter = ('status', 'booking_time', 'bus__route', 'seat_class')
    search_fields = ('user__email', 'user__full_name', 'bus__bus_number')
    date_hierarchy = 'booking_time'
    readonly_fields = ('booking_time', 'passenger_count')
    inlines = [MultiStopPassengerInline]
    exclude = ('passengers',)
    
    actions = ['mark_as_cancelled', 'mark_as_completed']
    
    def mark_as_cancelled(self, request, queryset):
        for ticket in queryset.filter(status='BOOKED'):
            ticket.cancel()
        self.message_user(request, _("Selected tickets have been cancelled."))
    mark_as_cancelled.short_description = _("Mark selected tickets as cancelled")
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='BOOKED').update(status='COMPLETED')
        self.message_user(request, _("%s tickets have been marked as completed.") % updated)
    mark_as_completed.short_description = _("Mark selected tickets as completed")
    
    def passenger_count(self, obj):
        return obj.passengers.count()
    passenger_count.short_description = _("Number of passengers")
