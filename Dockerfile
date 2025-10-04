FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivo de dependencias
COPY requirements.txt requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del proyecto (NO backend/)
COPY . .

# Crear directorios necesarios
RUN mkdir -p static media logs

# Crear usuario no-root
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["sleep", "infinity"]
