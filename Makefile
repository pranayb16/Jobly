.PHONY: backend-install backend-test backend-lint frontend-install frontend-check migrate crawl enrich pipeline api docker-build

backend-install:
	cd backend && python -m pip install -e ".[dev]"

backend-test:
	cd backend && pytest

backend-lint:
	cd backend && ruff check .

frontend-install:
	cd frontend && npm ci

frontend-check:
	cd frontend && npm run check && npm run build

migrate:
	cd backend && python -m jobly.commands.migrate

crawl:
	cd backend && python -m jobly.commands.crawl

enrich:
	cd backend && python -m jobly.commands.enrich

pipeline:
	cd backend && python -m jobly.commands.pipeline

api:
	cd backend && uvicorn jobly.api.main:app --reload --port 8000

docker-build:
	docker build -f backend/Dockerfile -t jobly-backend .
