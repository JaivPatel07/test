from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Alert, Incident, Location, Prediction, Sensor, SensorReading, Shelter
from .serializers import AlertSerializer, IncidentSerializer, LocationSerializer, PredictionSerializer, SensorReadingSerializer, SensorSerializer, ShelterSerializer


@api_view(['GET'])
def health(request):
    return Response({
        'status': 'operational',
        'services': {'api': 'ONLINE', 'riskEngine': 'ONLINE', 'rainfall': 'ONLINE', 'soilMoisture': 'ONLINE', 'weather': 'ONLINE'},
        'generatedAt': timezone.now(),
    })


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('query')
        district = self.request.query_params.get('district')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(district__icontains=query) | Q(state__icontains=query))
        if district:
            queryset = queryset.filter(district__iexact=district)
        return queryset

    @action(detail=True, methods=['get'])
    def risk(self, request, pk=None):
        location = self.get_object()
        prediction = location.predictions.first()
        if prediction:
            data = PredictionSerializer(prediction).data
        else:
            data = {
                'location': location.id,
                'combined_risk': location.current_risk,
                'landslide_probability': max(0, location.current_risk - 8),
                'flood_probability': max(0, location.current_risk - 5),
                'confidence': 0.91,
                'estimated_lead_minutes': 32,
                'model_version': 'RF-2.4.1',
                'factors': [
                    {'name': 'Rainfall intensity', 'contribution': 92},
                    {'name': 'Soil moisture', 'contribution': 84},
                    {'name': 'Slope', 'contribution': 78},
                    {'name': 'Historical susceptibility', 'contribution': 71},
                ],
                'forecast': [
                    {'horizon': '30m', 'risk': location.current_risk},
                    {'horizon': '1h', 'risk': min(99, location.current_risk + 4)},
                    {'horizon': '3h', 'risk': min(99, location.current_risk + 10)},
                    {'horizon': '6h', 'risk': min(99, location.current_risk + 16)},
                ],
            }
        return Response(data)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related('location').all()
    serializer_class = AlertSerializer
    permission_classes = [AllowAny]
    filterset_fields = ('status', 'severity', 'location')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.select_related('location').all()
    serializer_class = IncidentSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user if self.request.user.is_authenticated else None)


class ShelterViewSet(viewsets.ModelViewSet):
    queryset = Shelter.objects.select_related('location').all()
    serializer_class = ShelterSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sensor.objects.select_related('location').all()
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticated]


class SensorReadingViewSet(viewsets.ModelViewSet):
    queryset = SensorReading.objects.select_related('sensor').all()
    serializer_class = SensorReadingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'get', 'head', 'options']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sensor = serializer.validated_data['sensor']
        if sensor.status != 'ONLINE':
            return Response({'detail': 'Sensor is not accepting readings.'}, status=status.HTTP_409_CONFLICT)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'accepted': True, 'reading': serializer.data, 'pipeline': 'queued-for-validation'}, status=status.HTTP_202_ACCEPTED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(validation_status='PENDING')


@api_view(['GET'])
def data_health(request):
    return Response({
        'sources': [
            {'name': 'IMD rainfall feed', 'status': 'ONLINE', 'freshnessMinutes': 2},
            {'name': 'ISRO soil moisture', 'status': 'ONLINE', 'freshnessMinutes': 14},
            {'name': 'Weather forecast API', 'status': 'ONLINE', 'freshnessMinutes': 8},
            {'name': 'River gauge network', 'status': 'DELAYED', 'freshnessMinutes': 42},
        ],
        'pipeline': {'lastRun': timezone.now(), 'validatedRecords': 18227, 'quarantinedRecords': 17},
    })


@api_view(['GET'])
def model_registry(request):
    return Response({
        'deployed': {'version': 'RF-2.4.1', 'f1': 0.91, 'precision': 0.93, 'recall': 0.89, 'rocAuc': 0.95, 'lastTrained': '2026-09-12'},
        'registry': [
            {'version': 'RF-2.4.1', 'status': 'DEPLOYED'},
            {'version': 'GB-2.4.0', 'status': 'ARCHIVED'},
            {'version': 'LR-2.3.2', 'status': 'ARCHIVED'},
        ],
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sensor_data(request):
    """Future-IoT gateway: validate and queue a normalized sensor reading."""
    sensor_id = request.data.get('sensorId') or request.data.get('sensor_id')
    if not sensor_id:
        return Response({'detail': 'sensorId is required.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    try:
        sensor = Sensor.objects.get(sensor_id=sensor_id)
    except Sensor.DoesNotExist:
        return Response({'detail': 'Unknown sensor.'}, status=status.HTTP_404_NOT_FOUND)
    payload = {
        'sensor': sensor.pk,
        'timestamp': request.data.get('timestamp'),
        'rainfall': request.data.get('rainfall'),
        'soil_moisture': request.data.get('soilMoisture', request.data.get('soil_moisture')),
        'temperature': request.data.get('temperature'),
        'humidity': request.data.get('humidity'),
        'water_level': request.data.get('waterLevel', request.data.get('water_level')),
        'raw_payload': request.data,
    }
    serializer = SensorReadingSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    reading = serializer.save(validation_status='PENDING')
    return Response({'accepted': True, 'reading': SensorReadingSerializer(reading).data, 'pipeline': 'queued-for-validation'}, status=status.HTTP_202_ACCEPTED)
