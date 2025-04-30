#ARM-compatible Python image (for Pi 3/4)
FROM python:3.9-slim-bullseye

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies first (add any your project needs)
RUN apt-get update && apt-get install -y \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set the command to run your application
CMD ["python", "main.py", "start", "npm"]