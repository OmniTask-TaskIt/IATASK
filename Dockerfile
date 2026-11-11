FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema para compilar paquetes
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponer el puerto de Uvicorn
EXPOSE 8000

# Ejecutar el servidor (el ciclo lifespan levanta automáticamente el consumidor RabbitMQ)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]