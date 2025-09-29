# DaydreamShop - Backend Django con Event Bus

## 📋 Tabla de Contenidos
- [Descripción del Proyecto](#descripción-del-proyecto)
- [Arquitectura](#arquitectura)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Configuración Local](#configuración-local)
- [Docker](#docker)
- [Desarrollo](#desarrollo)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoreo y Logging](#monitoreo-y-logging)
- [Seguridad](#seguridad)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## 🎯 Descripción del Proyecto

**DaydreamShop** es una plataforma de shopping inteligente que combina e-commerce tradicional con capacidades de IA avanzadas. El backend está construido en Django con una arquitectura basada en Event Bus que permite comunicación desacoplada entre componentes y facilita la futura migración del módulo de IA a FastAPI.

### Objetivos Principales
- ✅ Backend Django robusto y escalable
- ✅ Arquitectura desacoplada con Event Bus
- ✅ Sistema de IA integrado para recomendaciones y búsqueda
- ✅ Preparado para migración a microservicios
- ✅ Deploy automatizado en Render.com
- ✅ Cumplimiento de mejores prácticas de desarrollo

## 🏗️ Arquitectura

### Diagrama de Alto Nivel
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Mobile App    │    │   Admin Panel   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Django Backend       │
                    │   (API Gateway + Core)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │       Event Bus           │
                    │    (Redis + Celery)      │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   AI Service      │  │ Scraping Service │  │ Recommendation   │
│   (Django App)    │  │   (Django App)   │  │   Service        │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Principios de Diseño
- **Event-Driven Architecture**: Comunicación asíncrona entre servicios
- **Single Responsibility**: Cada app Django tiene una responsabilidad específica
- **Loose Coupling**: Servicios se comunican solo a través de eventos
- **Scalability First**: Preparado para escalar horizontalmente
- **Future-Proof**: Fácil migración a microservicios

## 🛠️ Stack Tecnológico

### Backend Core
- **Framework**: Django 5.0+ con Django REST Framework 3.14+
- **Base de Datos**: PostgreSQL 15+ con extensión pgvector
- **Cache**: Redis 7+ con django-redis
- **Queue**: Celery 5.3+ con Redis como broker
- **Event Bus**: Django-EventBus + Redis pub/sub

### IA y Machine Learning
- **OpenAI**: GPT-4 para generación de contenido
- **Embeddings**: OpenAI text-embedding-ada-002
- **Vector Store**: PostgreSQL con pgvector para búsqueda semántica
- **ML Pipeline**: scikit-learn para recomendaciones

### Herramientas de Desarrollo
- **Python**: 3.11+
- **Package Manager**: Poetry para dependencias
- **Testing**: pytest + pytest-django + factory-boy
- **Code Quality**: black, isort, flake8, mypy
- **Pre-commit**: Hooks para calidad de código

### Infraestructura
- **Containerización**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Deployment**: Render.com
- **Monitoring**: Sentry + Django Debug Toolbar
- **Logging**: structlog + ELK stack

## 📁 Estructura del Proyecto

```
daydreamshop/
├── .github/                    # GitHub Actions workflows
├── .vscode/                    # VS Code configuration
├── backend/                    # Django project root
│   ├── manage.py
│   ├── daydreamshop/          # Project settings
│   │   ├── __init__.py
│   │   ├── settings/          # Split settings
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # Base settings
│   │   │   ├── local.py       # Local development
│   │   │   ├── production.py  # Production settings
│   │   │   └── test.py        # Test settings
│   │   ├── urls.py            # Main URL configuration
│   │   ├── wsgi.py            # WSGI application
│   │   └── asgi.py            # ASGI application
│   ├── apps/                   # Django applications
│   │   ├── __init__.py
│   │   ├── core/              # Core functionality
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── models.py      # Base models
│   │   │   ├── managers.py    # Custom managers
│   │   │   ├── permissions.py # Custom permissions
│   │   │   └── utils.py       # Utility functions
│   │   ├── users/             # User management
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── models.py      # User model
│   │   │   ├── serializers.py # DRF serializers
│   │   │   ├── views.py       # API views
│   │   │   ├── urls.py        # URL routing
│   │   │   ├── admin.py       # Admin interface
│   │   │   ├── tests/         # Test files
│   │   │   └── migrations/    # Database migrations
│   │   ├── products/          # Product catalog
│   │   ├── brands/            # Brand management
│   │   ├── cart/              # Shopping cart
│   │   ├── ai_service/        # AI functionality
│   │   ├── scraping/          # Web scraping
│   │   ├── recommendations/   # Recommendation system
│   │   └── events/            # Event bus
│   ├── static/                 # Static files
│   ├── media/                  # User uploaded files
│   ├── templates/              # HTML templates
│   ├── requirements/           # Python requirements
│   │   ├── base.txt            # Base dependencies
│   │   ├── local.txt           # Local development
│   │   ├── production.txt      # Production dependencies
│   │   └── test.txt            # Testing dependencies
│   └── manage.py
├── docker/                      # Docker configuration
│   ├── backend/                # Backend Dockerfile
│   ├── nginx/                  # Nginx configuration
│   └── postgres/               # PostgreSQL initialization
├── scripts/                     # Utility scripts
│   ├── setup.sh                # Initial setup
│   ├── deploy.sh               # Deployment script
│   └── backup.sh               # Database backup
├── docs/                        # Documentation
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore file
├── docker-compose.yml           # Docker Compose configuration
├── docker-compose.prod.yml      # Production Docker Compose
├── Dockerfile                   # Main Dockerfile
├── poetry.lock                  # Poetry lock file
├── pyproject.toml              # Poetry configuration
├── README.md                    # This file
└── Makefile                     # Development commands
```

## 🚀 Configuración Local

### Prerrequisitos
- Python 3.11+
- Docker y Docker Compose
- Poetry (opcional, pero recomendado)
- Git

### Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/yourusername/daydreamshop.git
cd daydreamshop

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 3. Iniciar con Docker
make up

# 4. Crear superusuario
make superuser

# 5. Acceder a la aplicación
# Backend: http://localhost:8000
# Admin: http://localhost:8000/admin
# API: http://localhost:8000/api/
```

### Configuración Manual (sin Docker)

```bash
# 1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate      # Windows

# 2. Instalar dependencias
pip install -r requirements/local.txt

# 3. Configurar base de datos PostgreSQL
# Crear base de datos y usuario

# 4. Ejecutar migraciones
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Ejecutar servidor
python manage.py runserver
```

## 🐳 Docker

### Configuración Mínima

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: daydreamshop
      POSTGRES_USER: daydreamshop
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
      - ./backend/static:/app/static
      - ./backend/media:/app/media
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://daydreamshop:${DB_PASSWORD}@db:5432/daydreamshop
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

### Dockerfile Optimizado

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements/ requirements/
COPY pyproject.toml poetry.lock ./

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements/production.txt

# Copiar código de la aplicación
COPY backend/ .

# Crear usuario no-root
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "daydreamshop.wsgi:application"]
```

### Comandos Docker Útiles

```bash
# Iniciar servicios
make up

# Detener servicios
make down

# Ver logs
make logs

# Ejecutar comandos en el contenedor
make shell

# Reconstruir imagen
make build

# Limpiar volúmenes
make clean
```

## 💻 Desarrollo

### Flujo de Trabajo Git

```bash
# 1. Crear rama para nueva funcionalidad
git checkout -b feature/nueva-funcionalidad

# 2. Desarrollar y hacer commits
git add .
git commit -m "feat: implementar nueva funcionalidad"

# 3. Push y crear Pull Request
git push origin feature/nueva-funcionalidad

# 4. Merge después de review
git checkout main
git pull origin main
git branch -d feature/nueva-funcionalidad
```

### Estándares de Código

#### Python
- **Formato**: Black para formateo automático
- **Imports**: isort para ordenar imports
- **Linting**: flake8 para análisis estático
- **Type Hints**: mypy para verificación de tipos

#### Django
- **Models**: Usar `AUTH_USER_MODEL` en lugar de importar User directamente
- **Views**: Class-based views con DRF serializers
- **URLs**: Incluir app_name en cada app
- **Admin**: Registrar todos los modelos relevantes

#### Configuración Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Estructura de Apps Django

#### Core App
```python
# apps/core/models.py
from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    """Modelo base con timestamps automáticos."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(TimeStampedModel):
    """Modelo base con soft delete."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        abstract = True
```

#### Users App
```python
# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    """Modelo de usuario personalizado."""
    email = models.EmailField(unique=True)
    style_preferences = models.JSONField(default=dict)
    size_profile = models.JSONField(default=dict)
    shopping_behavior = models.JSONField(default=dict)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = 'users_user'
```

#### Event Bus Implementation
```python
# apps/events/bus.py
import json
import redis
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

class EventBus:
    """Implementación del Event Bus usando Redis."""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.pubsub = self.redis_client.pubsub()
    
    def publish(self, event_type: str, event_data: dict):
        """Publica un evento en el bus."""
        event = {
            'type': event_type,
            'data': event_data,
            'timestamp': timezone.now().isoformat(),
            'version': '1.0'
        }
        
        self.redis_client.publish(
            f"events:{event_type}",
            json.dumps(event, cls=DjangoJSONEncoder)
        )
    
    def subscribe(self, event_type: str, handler):
        """Suscribe un handler a un tipo de evento."""
        self.pubsub.subscribe(f"events:{event_type}")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                handler(event_data)
```

### API Endpoints

#### URLs Principales
```python
# daydreamshop/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/cart/', include('apps.cart.urls')),
    path('api/v1/ai/', include('apps.ai_service.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

#### Ejemplo de View
```python
# apps/products/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product
from .serializers import ProductSerializer
from .filters import ProductFilter

class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet para productos."""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Búsqueda semántica de productos."""
        query = request.data.get('query', '')
        # Implementar búsqueda con embeddings
        return Response({'results': []})
```

## 🧪 Testing

### Configuración de Tests

```python
# backend/daydreamshop/settings/test.py
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Usar cache en memoria para tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Deshabilitar Celery en tests
CELERY_ALWAYS_EAGER = True
```

### Ejemplo de Test

```python
# apps/products/tests/test_models.py
import pytest
from django.test import TestCase
from factory.django import DjangoModelFactory
from apps.products.models import Product
from apps.brands.models import Brand

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
    
    name = "Test Product"
    price = 99.99
    brand = None

class ProductModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Test Brand")
        self.product = ProductFactory(brand=self.brand)
    
    def test_product_creation(self):
        """Test que un producto se crea correctamente."""
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.price, 99.99)
        self.assertEqual(self.product.brand, self.brand)
    
    def test_product_str_representation(self):
        """Test la representación string del producto."""
        expected = f"{self.product.name} - {self.product.brand.name}"
        self.assertEqual(str(self.product), expected)
```

### Comandos de Testing

```bash
# Ejecutar todos los tests
make test

# Ejecutar tests con coverage
make test-coverage

# Ejecutar tests específicos
make test-app users

# Ejecutar tests en paralelo
make test-parallel
```

## 🚀 Deployment

### Render.com Configuration

#### Build Command
```bash
pip install -r requirements/production.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

#### Start Command
```bash
gunicorn daydreamshop.wsgi:application --bind 0.0.0.0:$PORT
```

#### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# Redis
REDIS_URL=redis://host:port/0

# Django
DJANGO_SETTINGS_MODULE=daydreamshop.settings.production
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=.onrender.com

# OpenAI
OPENAI_API_KEY=your-openai-key

# Sentry
SENTRY_DSN=your-sentry-dsn
```

### Production Settings

```python
# backend/daydreamshop/settings/production.py
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Database
DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get('DATABASE_URL')
    )
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Sentry
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )
```

### GitHub Actions CI/CD

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/test.txt
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        python manage.py test --parallel
    
    - name: Run linting
      run: |
        black --check .
        isort --check-only .
        flake8 .
        mypy .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to Render
      uses: johnbeynon/render-deploy-action@v1.0.0
      with:
        service-id: ${{ secrets.RENDER_SERVICE_ID }}
        api-key: ${{ secrets.RENDER_API_KEY }}
```

## 📊 Monitoreo y Logging

### Logging Configuration

```python
# backend/daydreamshop/settings/base.py
import structlog

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}

# Structlog configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### Health Checks

```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """Health check endpoint para monitoreo."""
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'services': {}
    }
    
    # Database health
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Redis health
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['services']['redis'] = 'healthy'
        else:
            health_status['services']['redis'] = 'unhealthy'
    except Exception as e:
        health_status['services']['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Celery health
    try:
        from celery import current_app
        current_app.control.inspect().active()
        health_status['services']['celery'] = 'healthy'
    except Exception as e:
        health_status['services']['celery'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

## 🔒 Seguridad

### Security Headers

```python
# backend/daydreamshop/settings/production.py
# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
X_CONTENT_TYPE_OPTIONS = 'nosniff'
REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True

# Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### Authentication

```python
# apps/users/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

class CustomJWTAuthentication(JWTAuthentication):
    """Autenticación JWT personalizada."""
    
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None
        
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        # Verificar si el usuario está activo
        if not user.is_active:
            return None
        
        return (user, validated_token)

def get_tokens_for_user(user):
    """Genera tokens JWT para un usuario."""
    refresh = RefreshToken.for_user(user)
    
    # Agregar claims personalizados
    refresh['username'] = user.username
    refresh['email'] = user.email
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
```

## ⚡ Performance

### Database Optimization

```python
# apps/products/models.py
class Product(models.Model):
    # ... campos existentes ...
    
    class Meta:
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
            # Índice para búsqueda vectorial
            models.Index(fields=['embedding_vector'], name='product_embedding_idx'),
        ]
        
        # Particionamiento por brand para grandes volúmenes
        # partition_by = 'brand_id'
```

### Caching Strategy

```python
# apps/products/views.py
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

class ProductViewSet(viewsets.ModelViewSet):
    # ... configuración existente ...
    
    @method_decorator(cache_page(60 * 15))  # 15 minutos
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 60))  # 1 hora
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
```

### Celery Tasks Optimization

```python
# apps/ai_service/tasks.py
from celery import shared_task
from django.core.cache import cache

@shared_task(bind=True, max_retries=3)
def generate_product_embeddings(self, product_id):
    """Genera embeddings para un producto."""
    cache_key = f"embedding_generation_{product_id}"
    
    # Evitar procesamiento duplicado
    if cache.get(cache_key):
        return f"Embeddings already being generated for product {product_id}"
    
    cache.set(cache_key, True, timeout=300)  # 5 minutos
    
    try:
        product = Product.objects.get(id=product_id)
        # Generar embeddings...
        
        cache.delete(cache_key)
        return f"Embeddings generated for product {product_id}"
        
    except Exception as exc:
        cache.delete(cache_key)
        raise self.retry(exc=exc, countdown=60)
```

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error de Conexión a PostgreSQL
```bash
# Verificar que PostgreSQL esté corriendo
docker ps | grep postgres

# Ver logs del contenedor
docker logs daydreamshop_db_1

# Conectar manualmente
docker exec -it daydreamshop_db_1 psql -U daydreamshop -d daydreamshop
```

#### 2. Error de Redis
```bash
# Verificar Redis
docker exec -it daydreamshop_redis_1 redis-cli ping

# Ver logs
docker logs daydreamshop_redis_1
```

#### 3. Problemas de Migraciones
```bash
# Ver estado de migraciones
python manage.py showmigrations

# Aplicar migraciones específicas
python manage.py migrate --fake-initial

# Resetear migraciones (¡CUIDADO!)
python manage.py migrate --fake zero
python manage.py migrate --fake-initial
```

#### 4. Problemas de Dependencias
```bash
# Limpiar cache de pip
pip cache purge

# Reinstalar dependencias
pip install -r requirements/local.txt --force-reinstall

# Verificar versiones
pip list | grep Django
```

### Logs y Debugging

```bash
# Ver logs en tiempo real
docker-compose logs -f backend

# Ver logs específicos
docker-compose logs backend | grep ERROR

# Ejecutar shell de Django
make shell

# Ver variables de entorno
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DATABASES)
```

## 📚 Recursos Adicionales

### Documentación Oficial
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Mejores Prácticas
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Two Scoops of Django](https://www.twoscoopspress.com/books/two-scoops-of-django-3-x/)
- [Django REST Framework Best Practices](https://www.django-rest-framework.org/topics/best-practices/)

### Herramientas de Desarrollo
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Django Extensions](https://django-extensions.readthedocs.io/)
- [Django Silk](https://github.com/jazzband/django-silk)

---

## 🎉 Conclusión

Este proyecto está diseñado para ser **robusto, escalable y mantenible**, siguiendo las mejores prácticas de Django y arquitectura de software moderna. La implementación del Event Bus permite una comunicación desacoplada entre componentes, facilitando futuras migraciones y mantenimiento.

### Próximos Pasos
1. **Implementar Event Handlers** para cada tipo de evento
2. **Configurar Celery Workers** para procesamiento asíncrono
3. **Implementar sistema de logging** estructurado
4. **Configurar monitoreo** con Sentry o similar
5. **Implementar tests** para cada componente
6. **Configurar CI/CD** pipeline completo

### Contribución
Para contribuir al proyecto:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Implementa los cambios
4. Agrega tests
5. Crea un Pull Request

¡Happy coding! 🚀
