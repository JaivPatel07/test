from rest_framework import serializers
from .models import Alert, EnvironmentalReading, Incident, Location, Prediction, Sensor, SensorReading, Shelter


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentalReading
        fields = '__all__'


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = '__all__'


class AlertSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ('created_by', 'issued_at')


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = '__all__'
        read_only_fields = ('reported_by', 'created_at', 'status')


class ShelterSerializer(serializers.ModelSerializer):
    available_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shelter
        fields = '__all__'


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ('id', 'sensor_id', 'name', 'sensor_type', 'location', 'status', 'last_reading_at')


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = '__all__'
        read_only_fields = ('validation_status', 'created_at')

    def validate_soil_moisture(self, value):
        if value is not None and not 0 <= value <= 100:
            raise serializers.ValidationError('Soil moisture must be between 0 and 100.')
        return value
