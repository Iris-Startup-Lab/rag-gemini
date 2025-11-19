# Usamos una imagen ligera de Python 3.11
FROM python:3.11-slim

# Evitar archivos .pyc y hacer que el output se loguee directamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias de sistema mínimas (opcional, pero útil)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copiamos solo requirements primero para aprovechar caché de Docker
COPY requirements.txt .

# Instalamos dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Puerto por defecto (Railway suele poner $PORT, pero Uvicorn lo expondrá en 8000)
ENV PORT=8000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
