.PHONY: up down logs migrate test-api test-web lint build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd apps/api && alembic upgrade head

test-api:
	cd apps/api && pytest tests/ -v

test-web:
	cd apps/web && npm run test

lint:
	cd apps/api && ruff format --check . && ruff check . && mypy app
	cd apps/web && npm run lint

build:
	cd apps/web && npm run build

test: test-api test-web lint build
