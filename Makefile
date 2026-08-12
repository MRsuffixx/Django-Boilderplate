.PHONY: install install-advanced dev test test-cov lint format check migrate makemigrations shell superuser bootstrap seed docker-up docker-down docker-logs collectstatic worker beat schema

install:
	uv sync --extra dev
	uv run pre-commit install

install-advanced:
	uv sync --all-extras
	uv run pre-commit install

dev:
	uv run python manage.py runserver

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

check:
	uv run python manage.py check
	uv run python manage.py makemigrations --check --dry-run

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

shell:
	uv run python manage.py shell

superuser:
	uv run python manage.py createsuperuser

bootstrap:
	uv run python manage.py bootstrap

seed:
	uv run python manage.py seed

collectstatic:
	uv run python manage.py collectstatic --noinput

worker:
	uv run celery -A config.celery worker --loglevel=INFO

beat:
	uv run celery -A config.celery beat --loglevel=INFO

schema:
	uv run python manage.py spectacular --file schema.yml --validate

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f web celery_worker celery_beat
