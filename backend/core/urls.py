from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AlertViewSet, IncidentViewSet, LocationViewSet, SensorReadingViewSet, SensorViewSet, ShelterViewSet, data_health, health, model_registry

router = DefaultRouter()
router.register('locations', LocationViewSet, basename='location')
router.register('alerts', AlertViewSet, basename='alert')
router.register('incidents', IncidentViewSet, basename='incident')
router.register('shelters', ShelterViewSet, basename='shelter')
router.register('sensors', SensorViewSet, basename='sensor')
router.register('sensor-readings', SensorReadingViewSet, basename='sensor-reading')

urlpatterns = [
    path('health/', health, name='health'),
    path('data-health/', data_health, name='data-health'),
    path('models/', model_registry, name='model-registry'),
    path('', include(router.urls)),
]

# The explicit gateway route mirrors the public integration contract.
from .views import sensor_data
urlpatterns.insert(1, path('sensors/data/', sensor_data, name='sensor-data'))
