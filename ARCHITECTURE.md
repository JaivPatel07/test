# Aegis Terrain

Aegis Terrain is a frontend-first prototype for a hyper-local landslide and flash-flood decision-support platform for hilly regions of India. The prototype intentionally uses clearly labelled simulated readings and shows the production integration seams without pretending that the current values are official forecasts.

## Product flow

```text
Rainfall / weather / soil moisture / terrain / river gauges / history / field reports
        -> validate and freshness-check
        -> feature engineering at village or ward geometry
        -> landslide model + flash-flood model
        -> combined risk engine + lead-time estimator
        -> explainability + escalation policy
        -> warning, action recommendations, evacuation and response tracking
```

## Frontend routes represented by the prototype

- Command center
- Hyper-local risk map and location profile drawer
- Early warning center
- Incident reports and response queue
- Evacuation and shelter capacity
- Emergency resources
- Analytics and reports
- Historical disaster comparison
- Scenario simulation
- Data health and future IoT gateway
- Model monitoring and registry
- System settings
- Citizen safety view

## Production service boundary

The current UI uses deterministic mock data in `app.js` so it can be previewed without credentials, a database, or physical sensors. In production, the UI should call a versioned API using relative URLs:

```text
GET  /api/v1/locations?query=...
GET  /api/v1/locations/:id/risk
GET  /api/v1/locations/:id/forecast
GET  /api/v1/rainfall?location_id=...
GET  /api/v1/alerts?status=active
POST /api/v1/alerts
POST /api/v1/incidents
GET  /api/v1/shelters?near=...
POST /api/v1/sensors/data
GET  /api/v1/data-health
GET  /api/v1/models/registry
```

Recommended implementation:

- React or Next.js for the UI and route-level code splitting
- FastAPI for REST and WebSocket services
- PostgreSQL + PostGIS for locations, boundaries and spatial queries
- Redis + Celery for ingestion, model inference and alert jobs
- Object storage with malware scanning for incident media
- JWT or secure HTTP-only session cookies with RBAC and audit logging
- Leaflet, MapLibre or OpenLayers backed by approved district boundary and terrain tiles

## Domain model

The backend should keep separate tables for `User`, `Role`, `Location`, `Village`, `Ward`, `RainfallRecord`, `SoilMoistureRecord`, `WeatherRecord`, `TerrainData`, `HistoricalDisaster`, `Prediction`, `RiskScore`, `Alert`, `Incident`, `Shelter`, `EvacuationPlan`, `ResponseTeam`, `EmergencyResource`, `Sensor`, `SensorReading`, `Notification`, `AuditLog`, `ModelVersion` and `DataSource`.

The sensor gateway must validate sensor identity, timestamp, coordinates, units and range before a reading can enter the feature store. Stale or quarantined feeds must be visible in Data Health and must not silently trigger escalation.

## Safety and model governance

Each prediction should persist:

- probability and risk category
- confidence and model version
- generated timestamp and source freshness
- input snapshot / feature values
- top contributing factors
- estimated lead time with uncertainty

The product should communicate that it estimates probability from available environmental data. It does not know the exact time of a disaster and never replaces official disaster-management instructions.
