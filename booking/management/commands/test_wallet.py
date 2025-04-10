from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from booking.models import Wallet
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Test wallet functionality by adding and checking funds'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user whose wallet to test')
        parser.add_argument('amount', type=float, help='Amount to add to the wallet')

    def handle(self, *args, **options):
        email = options['email']
        amount_float = options['amount']
        
        # Convert to Decimal for proper handling
        amount = Decimal(str(amount_float))
        
        self.stdout.write(self.style.WARNING(f"Testing wallet for user: {email}"))
        
        try:
            # Get the user
            user = User.objects.get(email=email)
            self.stdout.write(self.style.SUCCESS(f"Found user: {user.full_name}"))
            
            # Get or create wallet
            try:
                wallet = user.wallet
                self.stdout.write(f"Initial wallet balance: ₹{wallet.balance}")
            except Wallet.DoesNotExist:
                wallet = Wallet.objects.create(user=user)
                self.stdout.write(self.style.WARNING("Created new wallet with balance: ₹0"))
            
            # Perform deposit with transaction
            try:
                with transaction.atomic():
                    initial_balance = wallet.balance
                    result = wallet.deposit(amount, "Test deposit via management command")
                    
                    # Refresh from database to ensure we see updated values
                    wallet.refresh_from_db()
                    
                    if result:
                        self.stdout.write(self.style.SUCCESS(
                            f"✅ Successfully added ₹{amount} to wallet"
                        ))
                        self.stdout.write(self.style.SUCCESS(
                            f"Initial balance: ₹{initial_balance} → New balance: ₹{wallet.balance}"
                        ))
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"❌ Failed to add funds to wallet"
                        ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during deposit: {str(e)}"))
                
            # Show latest transactions
            self.stdout.write("\nRecent transactions:")
            for tx in wallet.transactions.all()[:5]:
                self.stdout.write(f"- {tx.transaction_type}: ₹{tx.amount} - {tx.description} ({tx.timestamp})")
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email {email} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}")) 