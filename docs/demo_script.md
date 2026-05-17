# Demo Script (7-9 min)

1. Start stack (`docker compose up --build -d`).
2. Show architecture diagram from `docs/architecture.md`.
3. Open `http://localhost:8180/docs`.
4. Call `POST /workflow/consultation` with sample payload.
5. Show returned objects:
   - appointment,
   - payment,
   - video session,
   - EMR entry,
   - critical alerts.
6. Open EMR endpoint and show FHIR bundle:
   - `GET /emr/fhir/{patient_id}` via emr-service docs.
7. Show health and KPI:
   - `GET /services/health`,
   - `GET /analytics/kpi`.
8. Open frontend `http://localhost:5174` and switch RU/EN/KK + role view.
9. Show notification history endpoint.
10. Finish with roadmap and production hardening plan.
