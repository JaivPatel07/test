from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Alert, Location, Prediction, Sensor, Shelter


LOCATIONS = [
    ('Karsog', 86, 'CRITICAL', 8420, 68, 88, 37),
    ('Thunag', 74, 'VERY HIGH', 5680, 54, 79, 42),
    ('Janjehli', 69, 'HIGH', 4210, 48, 72, 34),
    ('Sundernagar', 57, 'HIGH', 12900, 41, 68, 26),
    ('Aut', 43, 'MODERATE', 3160, 29, 58, 24),
    ('Gohar', 31, 'MODERATE', 6730, 22, 46, 19),
    ('Pandoh', 22, 'LOW', 2840, 16, 35, 16),
]


class Command(BaseCommand):
    help = 'Create the demo Mandi district dataset and officer account.'

    def handle(self, *args, **options):
        locations = []
        for name, risk, level, population, rainfall, moisture, slope in LOCATIONS:
            location, _ = Location.objects.update_or_create(
                name=name,
                defaults={'current_risk': risk, 'risk_level': level, 'population': population},
            )
            locations.append((location, rainfall, moisture, slope))
            Prediction.objects.filter(location=location).delete()
            Prediction.objects.create(
                location=location,
                landslide_probability=max(0, risk - 8),
                flood_probability=max(0, risk - 5),
                combined_risk=risk,
                confidence=0.91,
                estimated_lead_minutes=32 if name == 'Karsog' else 48,
                factors=[
                    {'name': 'Rainfall intensity', 'contribution': 92},
                    {'name': 'Soil moisture', 'contribution': 84},
                    {'name': 'Slope', 'contribution': 78},
                    {'name': 'Historical susceptibility', 'contribution': 71},
                ],
            )
        Shelter.objects.get_or_create(name='Karsog Community Hall', defaults={'location': locations[0][0], 'capacity': 280, 'occupied': 211, 'status': 'OPEN'})
        Shelter.objects.get_or_create(name='Thunag Sports Complex', defaults={'location': locations[1][0], 'capacity': 420, 'occupied': 420, 'status': 'FULL'})
        Shelter.objects.get_or_create(name='Janjehli Primary School', defaults={'location': locations[2][0], 'capacity': 180, 'occupied': 46, 'status': 'OPEN'})
        Sensor.objects.get_or_create(sensor_id='KGS-044', defaults={'name': 'Karsog sensor cluster', 'sensor_type': 'soil-moisture', 'location': locations[0][0]})
        User = get_user_model()
        user, created = User.objects.get_or_create(username='riya@aegisterrain.in', defaults={'email': 'riya@aegisterrain.in', 'first_name': 'Riya', 'last_name': 'Pradhan', 'is_staff': True})
        user.set_password('demo123')
        user.save()
        self.stdout.write(self.style.SUCCESS('Demo dataset ready. Officer: riya@aegisterrain.in / demo123'))
