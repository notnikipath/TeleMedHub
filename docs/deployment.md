# Deployment Guide

## Prerequisites

- Docker 24+
- Docker Compose v2+
- Python 3.11+ (for local tests/scripts)

## Run locally

```bash
docker compose up --build -d
```

Check:

```bash
curl http://localhost:8180/health
curl http://localhost:8180/services/health
```

Stop:

```bash
docker compose down
```

## Service ports

- API Gateway: `8180`
- Frontend: `5174`
- Appointment: `8101`
- Consultation: `8102`
- EMR: `8103`
- Device Integration: `8104`
- Analytics: `8105`
- Notification: `8106`
- Billing: `8107`
- Janus: `8188`

## Data stores and infra

- PostgreSQL: host port `55432`
- MongoDB: host port `27028`
- MinIO: host ports `9100`/`9101`
- RabbitMQ: host ports `5673`/`15673`
- Redis: host port `6380`

## Demo scripts

Generate sample data:

```bash
python scripts/generate_sample_data.py --count 3000
```

Run end-to-end pipeline demo:

```bash
python scripts/demo_pipeline.py
```
