.PHONY: dev-up dev-down prod-up prod-down build logs migrate makemigrations createsuperuser shell test collectstatic local-run local-test

# --- Development Environment (DB & Redis only) ---
dev-up:
	docker compose up -d

dev-down:
	docker compose down

# --- Production / Full Stack Environment ---
prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-restart:
	docker compose -f docker-compose.prod.yml restart

logs:
	docker compose -f docker-compose.prod.yml logs -f

# --- Django Commands inside Production Web Container ---
migrate:
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate

makemigrations:
	docker compose -f docker-compose.prod.yml exec web python manage.py makemigrations

createsuperuser:
	docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

shell:
	docker compose -f docker-compose.prod.yml exec web python manage.py shell

test:
	docker compose -f docker-compose.prod.yml exec web python manage.py test

collectstatic:
	docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

generate-data:
	docker compose -f docker-compose.prod.yml exec web python manage.py generate_seed

# --- Local Environment Commands ---
local-run:
	python manage.py runserver 0.0.0.0:8000

local-test:
	python manage.py test
