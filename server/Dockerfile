FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set default env vars
ENV DATA_DIR="/app/data"
ENV CLIENT_PUBLIC_DIR="/app/shared"

# Use -u to pass stdout to docker logs unbuffered
CMD ["python", "-u", "watch.py"]
