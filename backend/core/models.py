from django.conf import settings
from django.db import models


class Location(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MODERATE = 'MODERATE', 'Moderate'
        HIGH = 'HIGH', 'High'
        VERY_HIGH = 'VERY HIGH', 'Very high'
        CRITICAL = 'CRITICAL', 'Critical'

    name = models.CharField(max_length=160)
    district = models.CharField(max_length=120, default='Mandi')
    state = models.CharField(max_length=120, default='Himachal Pradesh')
    location_type = models.CharField(max_length=30, default='VILLAGE')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    population = models.PositiveIntegerField(default=0)
    current_risk = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-current_risk', 'name']
        indexes = [models.Index(fields=['district', 'name'])]

    def __str__(self):
        return f'{self.name}, {self.district}'


class EnvironmentalReading(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='readings')
    observed_at = models.DateTimeField()
    rainfall_1h = models.FloatField(default=0)
    rainfall_3h = models.FloatField(default=0)
    rainfall_24h = models.FloatField(default=0)
    soil_moisture = models.FloatField(default=0)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    river_level = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=120, default='simulated')
    is_validated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-observed_at']
        indexes = [models.Index(fields=['location', '-observed_at'])]


class Prediction(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='predictions')
    generated_at = models.DateTimeField(auto_now_add=True)
    model_version = models.CharField(max_length=80, default='RF-2.4.1')
    landslide_probability = models.FloatField(default=0)
    flood_probability = models.FloatField(default=0)
    combined_risk = models.PositiveSmallIntegerField(default=0)
    confidence = models.FloatField(default=0)
    estimated_lead_minutes = models.PositiveIntegerField(null=True, blank=True)
    factors = models.JSONField(default=list, blank=True)
    forecast = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-generated_at']


class Alert(models.Model):
    class Severity(models.TextChoices):
        ADVISORY = 'ADVISORY', 'Advisory'
        WATCH = 'WATCH', 'Watch'
        WARNING = 'WARNING', 'Warning'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=20, choices=Severity.choices)
    event_type = models.CharField(max_length=60)
    probability = models.FloatField(default=0)
    lead_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    message = models.TextField()
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-issued_at']


class Incident(models.Model):
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name='incidents')
    incident_type = models.CharField(max_length=60)
    description = models.TextField()
    severity = models.CharField(max_length=20, default='MODERATE')
    status = models.CharField(max_length=20, default='UNVERIFIED')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    media = models.FileField(upload_to='incidents/%Y/%m/', null=True, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    observed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Shelter(models.Model):
    name = models.CharField(max_length=180)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name='shelters')
    address = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    occupied = models.PositiveIntegerField(default=0)
    contact = models.CharField(max_length=80, blank=True)
    facilities = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default='OPEN')

    @property
    def available_capacity(self):
        return max(0, self.capacity - self.occupied)


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    sensor_type = models.CharField(max_length=60)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name='sensors')
    status = models.CharField(max_length=20, default='ONLINE')
    last_reading_at = models.DateTimeField(null=True, blank=True)
    api_key_hash = models.CharField(max_length=128, blank=True)


class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField()
    rainfall = models.FloatField(null=True, blank=True)
    soil_moisture = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    water_level = models.FloatField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    validation_status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
