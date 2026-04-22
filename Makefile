.PHONY: up down reset seed ingest test web-test lint

up:
	docker compose up --build

up-d:
	docker compose up --build -d

down:
	docker compose down

reset:
	docker compose down -v

seed:
	docker compose exec api python -m app.scripts.seed_all

ingest:
	docker compose exec api python -m app.scripts.ingest_all

test:
	docker compose exec api pytest

web-test:
	docker compose exec web npm test

lint:
	docker compose exec api ruff check .
	docker compose exec web npm run lint

logs:
	docker compose logs -f api

shell-api:
	docker compose exec api bash

shell-web:
	docker compose exec web sh
