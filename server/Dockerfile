FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set default env vars
ENV DATA_DIR="/app/data"
ENV CLIENT_PUBLIC_DIR="/app/shared"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# The API is the only process that runs the ETL (PYTHONUNBUFFERED above keeps the logs live)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
