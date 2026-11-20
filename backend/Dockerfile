# Lightweight Python base image
FROM python:3.11-slim

# Do not write .pyc files and flush logs straight to the console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the dependencies first so this layer is cached when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API code and the serialized model
COPY app.py superkart_model.joblib ./

EXPOSE 7860

# Serve the Flask app (object `superkart_api` in app.py) with 2 Gunicorn workers on port 7860
CMD ["gunicorn", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--bind", "0.0.0.0:7860", "app:superkart_api"]
