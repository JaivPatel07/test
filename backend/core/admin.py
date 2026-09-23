from django.contrib import admin
from .models import Alert, AuditLog, EnvironmentalReading, Incident, Location, Prediction, Sensor, SensorReading, Shelter


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'state', 'current_risk', 'risk_level', 'updated_at')
    list_filter = ('district', 'risk_level', 'location_type')
    search_fields = ('name', 'district', 'state')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'severity', 'event_type', 'status', 'issued_at')
    list_filter = ('severity', 'status', 'event_type')
    search_fields = ('location__name', 'message')


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'incident_type', 'severity', 'status', 'created_at')
    list_filter = ('incident_type', 'severity', 'status')
    search_fields = ('description', 'location__name')


@admin.register(Shelter)
class ShelterAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity', 'occupied', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'address')


admin.site.register([EnvironmentalReading, Prediction, Sensor, SensorReading, AuditLog])
