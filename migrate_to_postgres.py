#!/usr/bin/env python
"""
Script to migrate data from SQLite to PostgreSQL
This script should be run after PostgreSQL is set up but before running the app in production.
"""
import os
import sys
import django
import time
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Bus_Booking.settings')

# Force SQLite for the initial data extraction
os.environ['USE_SQLITE'] = 'True'

# Initialize Django
django.setup()

# Import Django models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group
from django.contrib.sessions.models import Session
from django.contrib.sites.models import Site
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from accounts.models import User, OTP
from booking.models import Route, Bus, Passenger, Ticket, Wallet, Transaction

User = get_user_model()

# Function to extract data from SQLite
def extract_data():
    logger.info("Extracting data from SQLite database...")
    
    data = {
        'users': list(User.objects.all().values()),
        'groups': list(Group.objects.all().values()),
        'permissions': list(Permission.objects.all().values()),
        'content_types': list(ContentType.objects.all().values()),
        'sites': list(Site.objects.all().values()),
        'email_addresses': list(EmailAddress.objects.all().values()),
        'email_confirmations': list(EmailConfirmation.objects.all().values()),
        'social_apps': list(SocialApp.objects.all().values()),
        'social_accounts': list(SocialAccount.objects.all().values()),
        'social_tokens': list(SocialToken.objects.all().values()),
        'otps': list(OTP.objects.all().values()),
        'routes': list(Route.objects.all().values()),
        'buses': list(Bus.objects.all().values()),
        'passengers': list(Passenger.objects.all().values()),
        'tickets': list(Ticket.objects.all().values()),
        'wallets': list(Wallet.objects.all().values()),
        'transactions': list(Transaction.objects.all().values()),
    }
    
    # Get many-to-many data
    data['ticket_passengers'] = []
    for ticket in Ticket.objects.all():
        for passenger in ticket.passengers.all():
            data['ticket_passengers'].append({
                'ticket_id': ticket.id,
                'passenger_id': passenger.id
            })
    
    # Get user permissions and groups
    data['user_permissions'] = []
    data['user_groups'] = []
    
    for user in User.objects.all():
        for permission in user.user_permissions.all():
            data['user_permissions'].append({
                'user_id': user.id,
                'permission_id': permission.id
            })
        
        for group in user.groups.all():
            data['user_groups'].append({
                'user_id': user.id,
                'group_id': group.id
            })
    
    # Get group permissions
    data['group_permissions'] = []
    for group in Group.objects.all():
        for permission in group.permissions.all():
            data['group_permissions'].append({
                'group_id': group.id,
                'permission_id': permission.id
            })
    
    # Get social app sites
    data['social_app_sites'] = []
    for social_app in SocialApp.objects.all():
        for site in social_app.sites.all():
            data['social_app_sites'].append({
                'socialapp_id': social_app.id,
                'site_id': site.id
            })
    
    logger.info(f"Data extracted from SQLite. {len(data['users'])} users, {len(data['tickets'])} tickets.")
    return data

# Now switch to PostgreSQL for loading data
def load_data_to_postgres(data):
    # Remove the SQLite flag to use PostgreSQL
    if 'USE_SQLITE' in os.environ:
        del os.environ['USE_SQLITE']
    
    # Reload Django to use PostgreSQL settings
    for key in list(sys.modules.keys()):
        if key.startswith('django') or key.startswith('accounts') or key.startswith('booking'):
            del sys.modules[key]
    
    # Reinitialize Django with PostgreSQL
    django.setup()
    
    # Re-import models with new connection
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission, Group
    from django.contrib.sites.models import Site
    from allauth.account.models import EmailAddress, EmailConfirmation
    from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
    from accounts.models import User, OTP
    from booking.models import Route, Bus, Passenger, Ticket, Wallet, Transaction
    
    User = get_user_model()
    
    logger.info("Loading data to PostgreSQL database...")
    
    # Clear existing data
    Transaction.objects.all().delete()
    Wallet.objects.all().delete()
    Ticket.objects.all().delete()
    Passenger.objects.all().delete()
    Bus.objects.all().delete()
    Route.objects.all().delete()
    OTP.objects.all().delete()
    SocialToken.objects.all().delete()
    SocialAccount.objects.all().delete()
    SocialApp.objects.all().delete()
    EmailConfirmation.objects.all().delete()
    EmailAddress.objects.all().delete()
    User.objects.all().delete()
    
    # Load ContentTypes first (needed for permissions)
    for ct_data in data['content_types']:
        ContentType.objects.create(**ct_data)
    
    # Load Permissions
    for perm_data in data['permissions']:
        Permission.objects.create(**perm_data)
    
    # Load Groups
    group_map = {}
    for group_data in data['groups']:
        group_id = group_data.pop('id')
        group = Group.objects.create(**group_data)
        group_map[group_id] = group
    
    # Load Group Permissions
    for gp in data['group_permissions']:
        group = group_map[gp['group_id']]
        perm = Permission.objects.get(id=gp['permission_id'])
        group.permissions.add(perm)
    
    # Load Sites
    site_map = {}
    for site_data in data['sites']:
        site_id = site_data.pop('id')
        site = Site.objects.create(**site_data)
        site_map[site_id] = site
    
    # Load Users
    user_map = {}
    for user_data in data['users']:
        user_id = user_data.pop('id')
        user = User.objects.create(**user_data)
        user_map[user_id] = user
    
    # Load User Permissions
    for up in data['user_permissions']:
        user = user_map[up['user_id']]
        perm = Permission.objects.get(id=up['permission_id'])
        user.user_permissions.add(perm)
    
    # Load User Groups
    for ug in data['user_groups']:
        user = user_map[ug['user_id']]
        group = group_map[ug['group_id']]
        user.groups.add(group)
    
    # Load Social Apps
    social_app_map = {}
    for sa_data in data['social_apps']:
        sa_id = sa_data.pop('id')
        sa = SocialApp.objects.create(**sa_data)
        social_app_map[sa_id] = sa
    
    # Load Social App Sites
    for sas in data['social_app_sites']:
        app = social_app_map[sas['socialapp_id']]
        site = site_map[sas['site_id']]
        app.sites.add(site)
    
    # Load Email Addresses
    for ea_data in data['email_addresses']:
        user_id = ea_data.pop('user_id')
        ea_data['user'] = user_map[user_id]
        EmailAddress.objects.create(**ea_data)
    
    # Load Social Accounts
    social_account_map = {}
    for sa_data in data['social_accounts']:
        sa_id = sa_data.pop('id')
        user_id = sa_data.pop('user_id')
        sa_data['user'] = user_map[user_id]
        sa = SocialAccount.objects.create(**sa_data)
        social_account_map[sa_id] = sa
    
    # Load Social Tokens
    for st_data in data['social_tokens']:
        app_id = st_data.pop('app_id', None)
        account_id = st_data.pop('account_id')
        
        st_data['account'] = social_account_map[account_id]
        if app_id:
            st_data['app'] = social_app_map[app_id]
        
        SocialToken.objects.create(**st_data)
    
    # Load OTPs
    for otp_data in data['otps']:
        user_id = otp_data.pop('user_id', None)
        if user_id and user_id in user_map:
            otp_data['user'] = user_map[user_id]
        OTP.objects.create(**otp_data)
    
    # Load Routes
    route_map = {}
    for route_data in data['routes']:
        route_id = route_data.pop('id')
        route = Route.objects.create(**route_data)
        route_map[route_id] = route
    
    # Load Buses
    bus_map = {}
    for bus_data in data['buses']:
        bus_id = bus_data.pop('id')
        route_id = bus_data.pop('route_id')
        bus_data['route'] = route_map[route_id]
        bus = Bus.objects.create(**bus_data)
        bus_map[bus_id] = bus
    
    # Load Passengers
    passenger_map = {}
    for passenger_data in data['passengers']:
        passenger_id = passenger_data.pop('id')
        passenger = Passenger.objects.create(**passenger_data)
        passenger_map[passenger_id] = passenger
    
    # Load Wallets
    wallet_map = {}
    for wallet_data in data['wallets']:
        wallet_id = wallet_data.pop('id')
        user_id = wallet_data.pop('user_id')
        wallet_data['user'] = user_map[user_id]
        wallet = Wallet.objects.create(**wallet_data)
        wallet_map[wallet_id] = wallet
    
    # Load Tickets
    ticket_map = {}
    for ticket_data in data['tickets']:
        ticket_id = ticket_data.pop('id')
        user_id = ticket_data.pop('user_id')
        bus_id = ticket_data.pop('bus_id')
        
        ticket_data['user'] = user_map[user_id]
        ticket_data['bus'] = bus_map[bus_id]
        
        ticket = Ticket.objects.create(**ticket_data)
        ticket_map[ticket_id] = ticket
    
    # Load Ticket Passengers
    for tp in data['ticket_passengers']:
        ticket = ticket_map[tp['ticket_id']]
        passenger = passenger_map[tp['passenger_id']]
        ticket.passengers.add(passenger)
    
    # Load Transactions
    for transaction_data in data['transactions']:
        wallet_id = transaction_data.pop('wallet_id')
        transaction_data['wallet'] = wallet_map[wallet_id]
        Transaction.objects.create(**transaction_data)
    
    logger.info("Data loaded to PostgreSQL successfully.")

if __name__ == "__main__":
    try:
        logger.info("Starting data migration from SQLite to PostgreSQL...")
        
        # Extract data from SQLite
        data = extract_data()
        
        # Wait a bit to ensure transactions are complete
        time.sleep(1)
        
        # Load data to PostgreSQL
        load_data_to_postgres(data)
        
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        sys.exit(1) 