from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Search and main views
    path('', views.index, name='index'),
    path('search/', views.bus_search, name='bus_search'),
    path('bus/<int:bus_id>/', views.bus_detail, name='bus_detail'),
    path('bus/<int:bus_id>/seats/', views.view_seats, name='view_seats'),
    
    # Ticket booking flows
    path('book/<int:bus_id>/', views.book_ticket, name='book_ticket'),
    path('booking/verify-otp/', views.verify_booking_otp, name='verify_booking_otp'),
    path('booking/resend-otp/', views.resend_booking_otp, name='resend_booking_otp'),
    path('booking/confirm/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking/success/<int:ticket_id>/', views.booking_success, name='booking_success'),
    
    # User journeys and tickets
    path('my-journeys/', views.user_journeys, name='user_journeys'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/cancel/<int:ticket_id>/', views.cancel_ticket, name='cancel_ticket'),
    path('ticket/<int:ticket_id>/passenger/<int:passenger_id>/edit/', views.edit_passenger, name='edit_passenger'),
    path('ticket/<int:ticket_id>/passengers/', views.get_passenger_details, name='get_passenger_details'),
    
    # Wallet
    path('wallet/', views.wallet_detail, name='wallet_detail'),
    path('wallet/add/', views.add_funds, name='add_money'),
    path('wallet/transactions/', views.transaction_history, name='transaction_history'),
] 