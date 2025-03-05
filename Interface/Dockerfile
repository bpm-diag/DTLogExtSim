# Use a Python 3.12.9 base image 
FROM python:3.12.9-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set Flask environment for development
ENV FLASK_ENV=development

# Create a working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt 

# Copy the entire application
COPY ./Content /app 


ENV HOST_ADDRESS=0.0.0.0
ENV HOST_PORT=6660
ENV SERVICE_NAME="Interface"

# Expose the Flask port
EXPOSE $HOST_PORT

# Define the command to run your Flask app with the development server
CMD ["python", "app.py"]