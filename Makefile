.PHONY: up down lint test

up:
	docker compose up --build -d

down:
	docker compose down

lint:
	ruff check .

test:
	pytest -q
