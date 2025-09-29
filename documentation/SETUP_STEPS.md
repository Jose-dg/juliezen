# 🚀 Pasos para Configurar DaydreamShop desde Cero (Con Docker)

## 📋 Prerrequisitos
- Docker y Docker Compose instalados
- Git configurado
- **NO necesitas Python instalado localmente** - todo corre en Docker

## 🔧 Paso a Paso de Configuración

### 1. Crear Estructura del Proyecto

```bash
# Crear directorio del proyecto
mkdir daydreamshop
cd daydreamshop

# Crear estructura de directorios
mkdir -p backend/apps
mkdir -p backend/daydreamshop
mkdir -p docker/postgres
mkdir -p scripts
mkdir -p docs
mkdir -p requirements
```

### 2. Crear Archivos de Configuración Docker PRIMERO

```bash
# Crear archivos de configuración Docker
touch docker-compose.yml
touch Dockerfile
touch Makefile
touch env.example
touch .gitignore
touch pyproject.toml
touch .pre-commit-config.yaml
touch README.md
touch requirements/base.txt
touch requirements/local.txt
touch requirements/production.txt
touch requirements/test.txt
```

### 3. Crear Estructura de Apps (Sin Django Admin)

```bash
# Ir al directorio apps
cd backend/apps

# Crear directorios de apps manualmente
mkdir core
mkdir users
mkdir products
mkdir brands
mkdir cart
mkdir ai_service
mkdir scraping
mkdir recommendations
mkdir notifications
mkdir events

# Crear __init__.py en cada app
touch core/__init__.py
touch users/__init__.py
touch products/__init__.py
touch brands/__init__.py
touch cart/__init__.py
touch ai_service/__init__.py
touch scraping/__init__.py
touch recommendations/__init__.py
touch notifications/__init__.py
touch events/__init__.py

# Crear __init__.py en el directorio apps
touch __init__.py

# Crear estructura básica de cada app
for app in core users products brands cart ai_service scraping recommendations notifications events; do
    mkdir -p $app/migrations
    mkdir -p $app/tests
    touch $app/migrations/__init__.py
    touch $app/apps.py
    touch $app/models.py
    touch $app/views.py
    touch $app/urls.py
    touch $app/admin.py
    touch $app/serializers.py
    touch $app/filters.py
done
```

### 4. Crear Estructura Django Manualmente

```bash
# Volver al directorio backend
cd ..

# Crear archivos Django manualmente
touch manage.py
touch daydreamshop/__init__.py
touch daydreamshop/urls.py
touch daydreamshop/wsgi.py
touch daydreamshop/asgi.py

# Crear directorio settings
mkdir daydreamshop/settings
touch daydreamshop/settings/__init__.py
touch daydreamshop/settings/base.py
touch daydreamshop/settings/local.py
touch daydreamshop/settings/production.py
touch daydreamshop/settings/test.py
```

### 5. Crear Scripts y Docker

```bash
# Volver al directorio raíz
cd ..

# Crear scripts
touch scripts/setup.sh
touch scripts/deploy.sh
touch scripts/backup.sh
chmod +x scripts/setup.sh

# Crear archivos Docker
touch docker/postgres/init.sql
touch docker/backend/Dockerfile
touch docker/nginx/nginx.conf
```

### 6. Copiar Contenido de los Archivos

Ahora necesitas copiar el contenido de los archivos que ya creamos:
- `docker-compose.yml`
- `Dockerfile`
- `requirements/*.txt`
- `pyproject.toml`
- etc.

### 7. Levantar Docker y Crear Proyecto Django

```bash
# Construir imagen Docker
docker-compose build backend

# Levantar servicios
docker-compose up -d

# Esperar a que los servicios estén listos
sleep 10

# Crear proyecto Django DENTRO del contenedor
docker-compose exec backend django-admin startproject daydreamshop .

# Crear apps Django DENTRO del contenedor
docker-compose exec backend bash -c "cd apps && django-admin startapp core"
docker-compose exec backend bash -c "cd apps && django-admin startapp users"
docker-compose exec backend bash -c "cd apps && django-admin startapp products"
docker-compose exec backend bash -c "cd apps && django-admin startapp brands"
docker-compose exec backend bash -c "cd apps && django-admin startapp cart"
docker-compose exec backend bash -c "cd apps && django-admin startapp ai_service"
docker-compose exec backend bash -c "cd apps && django-admin startapp scraping"
docker-compose exec backend bash -c "cd apps && django-admin startapp recommendations"
docker-compose exec backend bash -c "cd apps && django-admin startapp notifications"
docker-compose exec backend bash -c "cd apps && django-admin startapp events"
```

### 8. Configurar Django Settings

```bash
# Copiar archivos de configuración al contenedor
docker cp daydreamshop/settings/base.py daydreamshop_backend_1:/app/daydreamshop/settings/
docker cp daydreamshop/settings/local.py daydreamshop_backend_1:/app/daydreamshop/settings/
docker cp daydreamshop/settings/production.py daydreamshop_backend_1:/app/daydreamshop/settings/
docker cp daydreamshop/settings/test.py daydreamshop_backend_1:/app/daydreamshop/settings/

# Copiar manage.py
docker cp manage.py daydreamshop_backend_1:/app/
```

### 9. Ejecutar Migraciones

```bash
# Ejecutar migraciones
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser

# Recolectar estáticos
docker-compose exec backend python manage.py collectstatic --noinput
```

## 🐳 Comandos Docker Completos

### **1. Configurar Variables de Entorno**
```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar .env con tus configuraciones
nano .env
```

### **2. Construir y Levantar Servicios**
```bash
# Construir imagen del backend
docker-compose build backend

# Levantar todos los servicios
docker-compose up -d

# Verificar servicios corriendo
docker-compose ps

# Ver logs
docker-compose logs -f
```

### **3. Verificar Servicios**
```bash
# Verificar PostgreSQL
docker-compose exec db pg_isready -U daydreamshop

# Verificar Redis
docker-compose exec redis redis-cli ping

# Verificar backend
curl http://localhost:8000/health/
```

## 🎯 Comandos Útiles

### **Docker**
```bash
# Iniciar servicios
make up

# Detener servicios
make down

# Ver logs
make logs

# Reconstruir
make build

# Shell del backend
make shell
```

### **Django (Dentro del Contenedor)**
```bash
# Ejecutar migraciones
make migrate

# Crear superusuario
make superuser

# Ejecutar tests
make test

# Recolectar estáticos
make collectstatic
```

## 📁 Estructura Final del Proyecto

```
daydreamshop/
├── backend/
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── core/
│   │   ├── users/
│   │   ├── products/
│   │   ├── brands/
│   │   ├── cart/
│   │   ├── ai_service/
│   │   ├── scraping/
│   │   ├── recommendations/
│   │   ├── notifications/
│   │   └── events/
│   ├── daydreamshop/
│   │   ├── __init__.py
│   │   ├── settings/
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── manage.py
├── docker/
├── scripts/
├── requirements/
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── .env
├── .gitignore
├── pyproject.toml
├── .pre-commit-config.yaml
└── README.md
```

## 🚀 Flujo Correcto con Docker

1. **Crear estructura de directorios**
2. **Crear archivos de configuración Docker**
3. **Levantar servicios Docker**
4. **Crear proyecto Django DENTRO del contenedor**
5. **Crear apps Django DENTRO del contenedor**
6. **Configurar settings y URLs**
7. **Ejecutar migraciones**

## ⚠️ **IMPORTANTE - Diferencias Clave:**

- **NO** ejecutar `django-admin` localmente
- **SÍ** ejecutar `django-admin` dentro del contenedor Docker
- **NO** necesitas Python instalado localmente
- **SÍ** necesitas Docker y Docker Compose
- **NO** crear archivos Django manualmente
- **SÍ** crear estructura de directorios primero

¡Ahora sí está correcto para usar Docker desde el inicio! 🐳
