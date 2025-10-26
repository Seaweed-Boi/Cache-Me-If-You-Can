FROM python:3.11-slim

WORKDIR /app

# Install minimal system deps for common Python packages
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc build-essential \
	&& rm -rf /var/lib/apt/lists/*

# Copy and install service-specific requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY . /app

ENV PYTHONUNBUFFERED=1
CMD ["python", "worker.py"]
