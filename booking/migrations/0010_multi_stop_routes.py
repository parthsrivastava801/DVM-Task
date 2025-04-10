from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.core.validators
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0002_bus_has_general_seats_bus_has_luxury_seats_and_more'),
    ]

    operations = [
        # Create new MultiStopRoute model
        migrations.CreateModel(
            name='MultiStopRoute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='route name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('is_active', models.BooleanField(default=True, verbose_name='is active')),
            ],
            options={
                'verbose_name': 'multi-stop route',
                'verbose_name_plural': 'multi-stop routes',
            },
        ),
        
        # Create RouteStop model
        migrations.CreateModel(
            name='RouteStop',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=100, verbose_name='city name')),
                ('sequence', models.PositiveIntegerField(verbose_name='stop sequence')),
                ('arrival_offset', models.DurationField(blank=True, 
                                                     help_text='Time offset from route start for arrival', 
                                                     null=True, 
                                                     verbose_name='arrival time offset')),
                ('departure_offset', models.DurationField(blank=True, 
                                                       help_text='Time offset from route start for departure', 
                                                       null=True, 
                                                       verbose_name='departure time offset')),
                ('is_boarding_point', models.BooleanField(default=True, verbose_name='is boarding point')),
                ('is_dropping_point', models.BooleanField(default=True, verbose_name='is dropping point')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                           related_name='stops', 
                                           to='booking.MultiStopRoute')),
            ],
            options={
                'verbose_name': 'route stop',
                'verbose_name_plural': 'route stops',
                'ordering': ['route', 'sequence'],
                'unique_together': {('route', 'sequence')},
            },
        ),
        
        # Create RouteSegment model
        migrations.CreateModel(
            name='RouteSegment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distance', models.DecimalField(blank=True, 
                                               decimal_places=2, 
                                               max_digits=8, 
                                               null=True, 
                                               verbose_name='distance (km)')),
                ('duration', models.DurationField(blank=True, 
                                                null=True, 
                                                verbose_name='estimated journey time')),
                ('base_fare_multiplier', models.DecimalField(decimal_places=2, 
                                                          default=1.0, 
                                                          help_text='Multiplier applied to the bus base fare for this segment', 
                                                          max_digits=3, 
                                                          verbose_name='base fare multiplier')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                           related_name='segments', 
                                           to='booking.MultiStopRoute')),
                ('start_stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                               related_name='departing_segments', 
                                               to='booking.RouteStop')),
                ('end_stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                             related_name='arriving_segments', 
                                             to='booking.RouteStop')),
            ],
            options={
                'verbose_name': 'route segment',
                'verbose_name_plural': 'route segments',
                'unique_together': {('route', 'start_stop', 'end_stop')},
            },
        ),
        
        # Create MultiStopBus model
        migrations.CreateModel(
            name='MultiStopBus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bus_number', models.CharField(max_length=20, unique=True, verbose_name='bus number')),
                ('departure_time', models.DateTimeField(verbose_name='departure time')),
                ('arrival_time', models.DateTimeField(verbose_name='arrival time')),
                ('total_seats', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], 
                                                          verbose_name='total seats')),
                ('available_seats', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0)], 
                                                              verbose_name='available seats')),
                ('fare', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='base fare')),
                ('sleeper_fare', models.DecimalField(blank=True, 
                                                  decimal_places=2, 
                                                  max_digits=10, 
                                                  null=True, 
                                                  verbose_name='sleeper fare')),
                ('luxury_fare', models.DecimalField(blank=True, 
                                                 decimal_places=2, 
                                                 max_digits=10, 
                                                 null=True, 
                                                 verbose_name='luxury fare')),
                ('has_general_seats', models.BooleanField(default=True, verbose_name='has general seats')),
                ('has_sleeper_seats', models.BooleanField(default=False, verbose_name='has sleeper seats')),
                ('has_luxury_seats', models.BooleanField(default=False, verbose_name='has luxury seats')),
                ('is_active', models.BooleanField(default=True, verbose_name='is active')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                           related_name='buses', 
                                           to='booking.MultiStopRoute')),
            ],
            options={
                'verbose_name': 'multi-stop bus',
                'verbose_name_plural': 'multi-stop buses',
                'ordering': ['departure_time'],
            },
        ),
        
        # Create MultiStopTicket model
        migrations.CreateModel(
            name='MultiStopTicket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking_time', models.DateTimeField(default=timezone.now, verbose_name='booking time')),
                ('status', models.CharField(choices=[('BOOKED', 'Booked'), 
                                                    ('CANCELLED', 'Cancelled'), 
                                                    ('COMPLETED', 'Completed')], 
                                           default='BOOKED', 
                                           max_length=20, 
                                           verbose_name='status')),
                ('total_fare', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='total fare')),
                ('seat_numbers', models.CharField(help_text='Comma-separated seat numbers', 
                                                max_length=255, 
                                                verbose_name='seat numbers')),
                ('seat_class', models.CharField(choices=[('GENERAL', 'General'), 
                                                       ('SLEEPER', 'Sleeper'), 
                                                       ('LUXURY', 'Luxury')], 
                                              default='GENERAL', 
                                              max_length=20, 
                                              verbose_name='seat class')),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, 
                                         related_name='tickets', 
                                         to='booking.MultiStopBus')),
                ('end_stop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, 
                                             related_name='arrival_tickets', 
                                             to='booking.RouteStop')),
                ('passengers', models.ManyToManyField(related_name='multistop_tickets', to='booking.Passenger')),
                ('start_stop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, 
                                               related_name='departure_tickets', 
                                               to='booking.RouteStop')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, 
                                          related_name='multistop_tickets', 
                                          to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'multi-stop ticket',
                'verbose_name_plural': 'multi-stop tickets',
                'ordering': ['-booking_time'],
            },
        ),
        
        # Add related_multistop_ticket field to Transaction model
        migrations.AddField(
            model_name='transaction',
            name='related_multistop_ticket',
            field=models.ForeignKey(blank=True, 
                                  null=True, 
                                  on_delete=django.db.models.deletion.SET_NULL, 
                                  related_name='transactions', 
                                  to='booking.MultiStopTicket'),
        ),
    ] 