from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
import os

class Command(BaseCommand):
    help = 'Setup Google OAuth credentials for django-allauth'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', type=str, help='Google OAuth Client ID')
        parser.add_argument('--client-secret', type=str, help='Google OAuth Client Secret')

    def handle(self, *args, **options):
        client_id = options.get('client_id') or os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = options.get('client_secret') or os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

        if not client_id or not client_secret:
            self.stdout.write(self.style.ERROR('Error: Client ID and Client Secret are required.'))
            self.stdout.write(self.style.NOTICE('You can provide them as arguments or set them as environment variables:'))
            self.stdout.write('  GOOGLE_OAUTH_CLIENT_ID')
            self.stdout.write('  GOOGLE_OAUTH_CLIENT_SECRET')
            return

        # Check if a Google SocialApp already exists
        google_app = SocialApp.objects.filter(provider='google').first()
        
        if google_app:
            # Update the existing app
            google_app.client_id = client_id
            google_app.secret = client_secret
            google_app.save()
            self.stdout.write(self.style.SUCCESS('Updated existing Google OAuth settings'))
        else:
            # Create a new SocialApp for Google
            google_app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=client_id,
                secret=client_secret,
                key=''  # Not used for Google OAuth
            )
            self.stdout.write(self.style.SUCCESS('Created new Google OAuth settings'))

        # Make sure all sites are associated with the Google app
        current_sites = google_app.sites.all()
        all_sites = Site.objects.all()
        
        # Add any sites that aren't already associated
        sites_to_add = [site for site in all_sites if site not in current_sites]
        if sites_to_add:
            google_app.sites.add(*sites_to_add)
            self.stdout.write(self.style.SUCCESS(f'Associated {len(sites_to_add)} site(s) with the Google OAuth app'))

        self.stdout.write(self.style.SUCCESS('Google OAuth setup complete'))
        
        # Provide next steps
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Make sure you have added the correct callback URL in your Google Developer Console:')
        site = Site.objects.get_current()
        callback_url = f"http://{site.domain}/accounts/google/login/callback/"
        self.stdout.write(f'   {callback_url}')
        self.stdout.write('2. Add the client ID and secret to your .env file for future use:')
        self.stdout.write('   GOOGLE_OAUTH_CLIENT_ID=your_client_id')
        self.stdout.write('   GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret') 