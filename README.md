# TeleMedHub

Платформа для телемедицинских консультаций, ведения ЭМК и мониторинга пациентов.

## Реализовано

- Микросервисная архитектура:
  - `api-gateway`
  - `appointment-service`
  - `consultation-service`
  - `emr-service`
  - `device-integration`
  - `analytics-service`
  - `notification-service`
  - `billing-service`
- Видеоконсультации с WebRTC-сигналингом и балансировкой видео-нод.
- ЭМК с FHIR bundle, разграничением доступа и аудитом.
- Интеграция с устройствами (тонометр, глюкометр, пульсоксиметр, холтер).
- Мониторинг качества связи и критических показателей.
- Многоязычный интерфейс: `ru`, `en`, `kk`.

## Полный пайплайн консультации

`Запись -> Подтверждение -> Оплата -> Видео -> Заключение -> ЭМК -> Уведомления`

Endpoint:

- `POST /workflow/consultation` (API Gateway)

## Быстрый запуск

```bash
docker compose up --build -d
```

Проверка:

```bash
curl http://localhost:8180/health
curl http://localhost:8180/services/health
```

Swagger:

- `http://localhost:8180/docs` (gateway)
- `http://localhost:8101/docs` ... `http://localhost:8107/docs` (services)

Frontend:

- `http://localhost:5174`

## Тесты и качество

```bash
pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -q
```

Load scripts:

- `tests/load/locustfile.py`
- `tests/load/k6_gateway.js`

## Документация

- Архитектура: `docs/architecture.md`
- API: `docs/api.md`
- Развёртывание: `docs/deployment.md`
- Безопасность: `docs/security_compliance.md`
- Опциональные улучшения: `docs/optional_improvements.md`
- Отчёт: `docs/project_report.md`
- Презентация: `docs/presentation_outline.md`
- Демо-скрипт: `docs/demo_script.md`

## Environment configuration

Before starting services, copy `.env.example` to `.env` and adjust it for your machine. Example passwords and keys are for local demonstration only.

```powershell
Copy-Item .env.example .env
```
