#!/bin/bash

# Script de configuración inicial para DaydreamShop
# Este script configura el proyecto desde cero

set -e

echo "🚀 Configurando DaydreamShop..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar prerrequisitos
check_prerequisites() {
    print_status "Verificando prerrequisitos..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado. Por favor instala Docker primero."
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose no está instalado. Por favor instala Docker Compose primero."
        exit 1
    fi
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 no está instalado. Por favor instala Python 3.11+ primero."
        exit 1
    fi
    
    # Verificar versión de Python
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
        print_warning "Python $PYTHON_VERSION detectado. Se recomienda Python 3.11+"
    fi
    
    print_success "Prerrequisitos verificados correctamente"
}

# Configurar variables de entorno
setup_environment() {
    print_status "Configurando variables de entorno..."
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_success "Archivo .env creado desde env.example"
        else
            print_warning "No se encontró env.example. Crea manualmente el archivo .env"
        fi
    else
        print_status "Archivo .env ya existe"
    fi
}

# Construir y levantar servicios
start_services() {
    print_status "Construyendo y levantando servicios..."
    
    # Construir imagen del backend
    docker-compose build backend
    
    # Levantar servicios
    docker-compose up -d
    
    print_success "Servicios iniciados correctamente"
}

# Esperar a que los servicios estén listos
wait_for_services() {
    print_status "Esperando a que los servicios estén listos..."
    
    # Esperar a PostgreSQL
    print_status "Esperando PostgreSQL..."
    until docker-compose exec -T db pg_isready -U daydreamshop; do
        sleep 2
    done
    print_success "PostgreSQL está listo"
    
    # Esperar a Redis
    print_status "Esperando Redis..."
    until docker-compose exec -T redis redis-cli ping; do
        sleep 2
    done
    print_success "Redis está listo"
    
    # Esperar al backend
    print_status "Esperando backend..."
    until curl -f http://localhost:8000/health/ > /dev/null 2>&1; do
        sleep 5
    done
    print_success "Backend está listo"
}

# Ejecutar migraciones
run_migrations() {
    print_status "Ejecutando migraciones de base de datos..."
    
    docker-compose exec -T backend python manage.py migrate
    
    print_success "Migraciones ejecutadas correctamente"
}

# Recolectar archivos estáticos
collect_static() {
    print_status "Recolectando archivos estáticos..."
    
    docker-compose exec -T backend python manage.py collectstatic --noinput
    
    print_success "Archivos estáticos recolectados correctamente"
}

# Crear superusuario
create_superuser() {
    print_status "¿Deseas crear un superusuario? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Creando superusuario..."
        docker-compose exec -T backend python manage.py createsuperuser
        print_success "Superusuario creado correctamente"
    else
        print_status "Omitiendo creación de superusuario"
    fi
}

# Mostrar información final
show_final_info() {
    echo ""
    echo "🎉 ¡DaydreamShop está configurado correctamente!"
    echo ""
    echo "📱 URLs de acceso:"
    echo "   Backend API: http://localhost:8000/api/"
    echo "   Admin Panel: http://localhost:8000/admin/"
    echo "   Health Check: http://localhost:8000/health/"
    echo ""
    echo "🐳 Comandos útiles:"
    echo "   Ver logs: make logs"
    echo "   Ejecutar tests: make test"
    echo "   Shell Django: make shell"
    echo "   Detener servicios: make down"
    echo ""
    echo "📚 Documentación: README.md"
    echo ""
    echo "¡Happy coding! 🚀"
}

# Función principal
main() {
    echo "=========================================="
    echo "    DaydreamShop Setup Script"
    echo "=========================================="
    echo ""
    
    check_prerequisites
    setup_environment
    start_services
    wait_for_services
    run_migrations
    collect_static
    create_superuser
    show_final_info
}

# Ejecutar script principal
main "$@"
