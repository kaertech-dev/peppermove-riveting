FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (adds gunicorn for production serving)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application files
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 5080

# Use gunicorn to serve the Flask app for production
CMD ["gunicorn", "--bind", "0.0.0.0:5080", "app:app", "--workers", "2"]
