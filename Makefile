.PHONY: help up down build shell logs clean test test-coverage superuser migrate makemigrations collectstatic lint format

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Iniciar servicios con Docker Compose
	docker-compose up -d

down: ## Detener servicios
	docker-compose down

build: ## Reconstruir imagen del backend
	docker-compose build backend

shell: ## Ejecutar shell de Django en el contenedor
	docker-compose exec backend python manage.py shell

logs: ## Ver logs de todos los servicios
	docker-compose logs -f

logs-backend: ## Ver logs del backend
	docker-compose logs -f backend

logs-db: ## Ver logs de la base de datos
	docker-compose logs -f db

logs-redis: ## Ver logs de Redis
	docker-compose logs -f redis

clean: ## Limpiar volúmenes y contenedores
	docker-compose down -v
	docker system prune -f

test: ## Ejecutar tests
	docker-compose exec backend python manage.py test

test-coverage: ## Ejecutar tests con coverage
	docker-compose exec backend coverage run --source='.' manage.py test
	docker-compose exec backend coverage report
	docker-compose exec backend coverage html

superuser: ## Crear superusuario
	docker-compose exec backend python manage.py createsuperuser

migrate: ## Aplicar migraciones
	docker-compose exec backend python manage.py migrate

makemigrations: ## Crear migraciones
	docker-compose exec backend python manage.py makemigrations

collectstatic: ## Recolectar archivos estáticos
	docker-compose exec backend python manage.py collectstatic --noinput

lint: ## Ejecutar linting
	docker-compose exec backend flake8 .
	docker-compose exec backend black --check .
	docker-compose exec backend isort --check-only .

format: ## Formatear código
	docker-compose exec backend black .
	docker-compose exec backend isort .

restart: ## Reiniciar servicios
	docker-compose restart

status: ## Ver estado de los servicios
	docker-compose ps

health: ## Verificar salud de los servicios
	@echo "Verificando salud de los servicios..."
	@curl -f http://localhost:8000/health/ || echo "Backend no está respondiendo"
	@docker-compose exec db pg_isready -U daydreamshop || echo "PostgreSQL no está respondiendo"
	@docker-compose exec redis redis-cli ping || echo "Redis no está respondiendo"

setup: ## Configuración inicial del proyecto
	@echo "Configurando proyecto DaydreamShop..."
	@make build
	@make up
	@sleep 10
	@make migrate
	@make collectstatic
	@echo "Proyecto configurado correctamente!"
	@echo "Accede a: http://localhost:8000"
	@echo "Admin: http://localhost:8000/admin"