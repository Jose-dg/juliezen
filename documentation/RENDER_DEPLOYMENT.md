# 🚀 Deployment en Render.com - DaydreamShop

## 📋 Prerrequisitos

- Cuenta en [Render.com](https://render.com)
- Repositorio Git configurado
- Variables de entorno preparadas

## 🔧 Configuración del Servicio

### 1. Crear Nuevo Web Service

1. **Ir a Dashboard** → **New** → **Web Service**
2. **Conectar repositorio** desde GitHub/GitLab
3. **Seleccionar rama**: `main` o `develop`

### 2. Configuración Básica

```yaml
# Nombre del servicio
Name: daydreamshop-backend

# Runtime: Python 3
Runtime: Python 3

# Build Command
Build Command: |
  pip install -r requirements/production.txt
  python manage.py collectstatic --noinput
  python manage.py migrate

# Start Command
Start Command: gunicorn daydreamshop.wsgi:application --bind 0.0.0.0:$PORT
```

### 3. Variables de Entorno

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=daydreamshop.settings.production
SECRET_KEY=tu-secret-key-super-segura-aqui
DEBUG=False
ALLOWED_HOSTS=.onrender.com

# Database (PostgreSQL de Render)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Redis (Redis de Render)
REDIS_URL=redis://user:password@host:port/0

# OpenAI
OPENAI_API_KEY=tu-openai-api-key

# Sentry (opcional)
SENTRY_DSN=tu-sentry-dsn

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

## 🗄️ Base de Datos PostgreSQL

### 1. Crear PostgreSQL Service

1. **New** → **PostgreSQL**
2. **Nombre**: `daydreamshop-db`
3. **Versión**: PostgreSQL 15
4. **Plan**: Free (para desarrollo) o Starter/Standard para producción

### 2. Configurar pgvector

```sql
-- Conectar a la base de datos y ejecutar:
CREATE EXTENSION IF NOT EXISTS vector;

-- Verificar instalación
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 3. Obtener DATABASE_URL

- Copiar la **Internal Database URL** desde el dashboard
- Formato: `postgresql://user:password@host:port/dbname`

## 🔴 Redis Service

### 1. Crear Redis Service

1. **New** → **Redis**
2. **Nombre**: `daydreamshop-redis`
3. **Plan**: Free (para desarrollo) o Starter para producción

### 2. Obtener REDIS_URL

- Copiar la **Internal Redis URL** desde el dashboard
- Formato: `redis://user:password@host:port/0`

## 🔄 Auto-Deploy

### 1. Configurar Webhook

- **Auto-Deploy**: Enabled
- **Branch**: `main`
- **Pull Request Deploy**: Enabled (opcional)

### 2. Health Check

```bash
# URL del health check
https://tu-servicio.onrender.com/health/

# Render verificará automáticamente este endpoint
```

## 📊 Monitoreo

### 1. Logs

- **Logs**: Disponibles en tiempo real en el dashboard
- **Log Retention**: 30 días (gratis) o 90 días (pago)

### 2. Metrics

- **CPU Usage**
- **Memory Usage**
- **Request Count**
- **Response Time**

### 3. Alerts

- Configurar alertas para:
  - CPU > 80%
  - Memory > 80%
  - Response Time > 5s

## 🚨 Troubleshooting

### 1. Build Failures

```bash
# Verificar logs de build
# Problemas comunes:
- Dependencias faltantes en requirements/production.txt
- Comandos de build incorrectos
- Variables de entorno faltantes
```

### 2. Runtime Errors

```bash
# Verificar logs de runtime
# Problemas comunes:
- DATABASE_URL incorrecta
- SECRET_KEY faltante
- ALLOWED_HOSTS mal configurado
```

### 3. Database Connection Issues

```bash
# Verificar:
- DATABASE_URL correcta
- PostgreSQL service activo
- pgvector extension instalada
```

## 🔒 Seguridad

### 1. Environment Variables

- **NUNCA** committear `.env` al repositorio
- Usar **Secrets** de Render para variables sensibles
- Rotar `SECRET_KEY` regularmente

### 2. CORS Configuration

```python
# backend/daydreamshop/settings/production.py
CORS_ALLOWED_ORIGINS = [
    "https://tu-frontend.com",
    "https://www.tu-frontend.com",
]

CORS_ALLOW_CREDENTIALS = True
```

### 3. Rate Limiting

```python
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

## 📈 Escalabilidad

### 1. Planes de Render

- **Free**: 750 horas/mes, sleep después de 15 min inactivo
- **Starter**: $7/mes, siempre activo, 512MB RAM
- **Standard**: $25/mes, siempre activo, 1GB RAM
- **Pro**: $50/mes, siempre activo, 2GB RAM

### 2. Optimizaciones

```python
# Configuración de Gunicorn para producción
# gunicorn.conf.py
workers = 4
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
```

### 3. CDN y Static Files

```python
# Usar WhiteNoise para archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# O configurar S3/CloudFront para producción
```

## 🔄 CI/CD con GitHub Actions

### 1. Workflow de Deploy

```yaml
# .github/workflows/deploy.yml
name: Deploy to Render

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Render
      uses: johnbeynon/render-deploy-action@v1.0.0
      with:
        service-id: ${{ secrets.RENDER_SERVICE_ID }}
        api-key: ${{ secrets.RENDER_API_KEY }}
```

### 2. Secrets de GitHub

- `RENDER_SERVICE_ID`: ID del servicio en Render
- `RENDER_API_KEY`: API Key de Render

## 📱 URLs de Acceso

### Desarrollo
- **Backend**: `http://localhost:8000`
- **API**: `http://localhost:8000/api/`
- **Admin**: `http://localhost:8000/admin/`

### Producción (Render)
- **Backend**: `https://tu-servicio.onrender.com`
- **API**: `https://tu-servicio.onrender.com/api/`
- **Admin**: `https://tu-servicio.onrender.com/admin/`

## 🎯 Checklist de Deployment

- [ ] Servicio web creado en Render
- [ ] PostgreSQL service configurado con pgvector
- [ ] Redis service configurado
- [ ] Variables de entorno configuradas
- [ ] Build exitoso
- [ ] Migraciones aplicadas
- [ ] Health check respondiendo
- [ ] SSL/HTTPS funcionando
- [ ] CORS configurado correctamente
- [ ] Logs monitoreándose
- [ ] Alerts configurados

## 🆘 Soporte

### Recursos Útiles
- [Render Documentation](https://render.com/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)

### Contacto
- **Render Support**: [support@render.com](mailto:support@render.com)
- **Django Community**: [Django Forum](https://forum.djangoproject.com/)

---

¡Tu DaydreamShop estará listo para producción en Render.com! 🚀
