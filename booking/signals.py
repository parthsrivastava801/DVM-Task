from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from django.conf import settings

from .models import Ticket, Wallet

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Create a wallet for newly registered users.
    """
    if created:
        Wallet.objects.create(user=instance)

@receiver(m2m_changed, sender=Ticket.passengers.through)
def update_available_seats_on_passenger_change(sender, instance, action, **kwargs):
    """
    Update available seats when passengers are added or removed from a ticket.
    """
    if action == 'post_add' and instance.status == 'BOOKED':
        # Decrease available seats when passengers are added
        bus = instance.bus
        passengers_count = instance.passengers.count()
        bus.available_seats = max(0, bus.available_seats - passengers_count)
        bus.save()
    
    elif action == 'post_remove' and instance.status == 'BOOKED':
        # Increase available seats when passengers are removed
        bus = instance.bus
        passengers_count = kwargs.get('pk_set', set())
        bus.available_seats = min(bus.total_seats, bus.available_seats + len(passengers_count))
        bus.save()

@receiver(pre_delete, sender=Ticket)
def update_available_seats_on_ticket_delete(sender, instance, **kwargs):
    """
    Update available seats when a ticket is deleted.
    """
    if instance.status == 'BOOKED':
        bus = instance.bus
        passengers_count = instance.passengers.count()
        bus.available_seats = min(bus.total_seats, bus.available_seats + passengers_count)
        bus.save() 