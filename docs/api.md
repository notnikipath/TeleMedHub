# API Documentation

## Swagger endpoints

- API Gateway: `http://localhost:8180/docs`
- Appointment: `http://localhost:8101/docs`
- Consultation: `http://localhost:8102/docs`
- EMR: `http://localhost:8103/docs`
- Device Integration: `http://localhost:8104/docs`
- Analytics: `http://localhost:8105/docs`
- Notification: `http://localhost:8106/docs`
- Billing: `http://localhost:8107/docs`

## Main endpoints

### API Gateway

- `POST /auth/token`
- `POST /auth/verify`
- `GET /services/health`
- `POST /recommend/doctor`
- `POST /workflow/consultation`

### Appointment Service

- `GET /doctors/{doctor_id}/calendar`
- `POST /appointments`
- `POST /appointments/{appointment_id}/confirm`
- `POST /appointments/{appointment_id}/cancel`
- `GET /appointments/{appointment_id}`
- `GET /reminders/due`
- `POST /symptoms/questionnaire`

### Consultation Service

- `POST /sessions/start`
- `POST /sessions/{session_id}/offer`
- `POST /sessions/{session_id}/answer`
- `POST /sessions/{session_id}/chat`
- `POST /sessions/{session_id}/files`
- `POST /sessions/{session_id}/quality`
- `POST /sessions/{session_id}/end`
- `POST /complaints/analyze`
- `POST /speech/protocol`

### EMR Service

- `POST /assignments`
- `POST /emr/entries`
- `POST /emr/patient/{patient_id}`
- `GET /emr/fhir/{patient_id}`
- `GET /emr/timeline/{patient_id}`
- `GET /access-log`

### Device Integration

- `POST /devices/register`
- `POST /devices/readings`
- `POST /devices/readings/bulk`
- `GET /devices/{patient_id}`
- `GET /devices/trends/{patient_id}`
- `GET /alerts/critical`

### Analytics Service

- `POST /analytics/ingest`
- `GET /analytics/diseases`
- `GET /analytics/treatment`
- `GET /analytics/doctor-load`
- `GET /analytics/kpi`
- `GET /dashboards/{role}`

### Notification Service

- `POST /notify/send`
- `POST /notify/template`
- `GET /notify/history`

### Billing Service

- `POST /payments/charge`
- `GET /payments/{transaction_id}`
- `POST /payments/refund`
- `POST /insurance/claim`
- `GET /insurance/claims`
