# TeleMedHub Architecture

## 1) High-level architecture

```mermaid
flowchart LR
    U[Users: Patient / Doctor / Admin / Insurer] --> FE[React + Redux Web App]
    FE --> GW[API Gateway]

    GW --> APT[Appointment Service]
    GW --> CNS[Consultation Service]
    GW --> EMR[EMR Service]
    GW --> DEV[Device Integration]
    GW --> ANL[Analytics Service]
    GW --> NTF[Notification Service]
    GW --> BIL[Billing Service]

    APT --> PG[(PostgreSQL)]
    EMR --> PG
    BIL --> PG
    EMR --> MONGO[(MongoDB Logs)]
    ANL --> MONGO
    EMR --> S3[(MinIO/S3 files)]
    CNS --> JANUS[Janus WebRTC]
    DEV --> MQ[(RabbitMQ)]
    NTF --> MQ
    EMR --> REDIS[(Redis EMR cache)]
```

## 2) Consultation pipeline

```mermaid
sequenceDiagram
    autonumber
    participant P as Patient
    participant GW as API Gateway
    participant A as Appointment
    participant B as Billing
    participant C as Consultation
    participant D as Device Integration
    participant E as EMR
    participant N as Notification
    participant X as Analytics

    P->>GW: Create consultation request
    GW->>A: Create appointment
    GW->>B: Online payment
    GW->>A: Confirm appointment
    GW->>C: Start video session (WebRTC signaling)
    GW->>D: Upload device readings (optional)
    D-->>GW: Critical alerts
    GW->>E: Save conclusion in EMR (FHIR-compatible)
    GW->>C: End session
    GW->>N: Send reminders/alerts
    GW->>X: Ingest KPI metrics
```

## 3) Security and compliance layer

- RBAC roles: `patient`, `doctor`, `admin`, `insurance_representative`.
- Access scoping:
  - patient: own data only;
  - doctor: assigned patients only;
  - admin: full management;
  - insurer: billing/coverage data only.
- Token-based auth with signed access tokens (JWT-like HMAC).
- Sensitive EMR fields encrypted before storage.
- Access audit log for every EMR read/write operation.
- Compliance-oriented controls for 152-ФЗ/HIPAA:
  - least privilege access,
  - auditability,
  - encrypted data in transit/storage (design-level).

## 4) Optional improvements implemented

1. NLP complaint analysis for pre-triage (Group A-1).
2. Speech-to-protocol auto-fill (Group A-2).
3. Doctor recommendation by symptoms (Group A-4).
4. Insurance integration (claims/approval API) (Group B-3).
5. Video node balancing across Janus nodes (Group C-1).
6. EMR caching for sub-2s reads (Group C-2).
7. Async file upload pipeline in consultation sessions (Group C-3).
8. Interactive symptom questionnaire (Group D-2).
