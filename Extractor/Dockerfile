# Use a Python 3.12.9 base image 
FROM python:3.12.9-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set Flask environment for development
ENV FLASK_ENV=development

RUN apt-get update && apt-get install -y openjdk-11-jdk && \
    apt-get clean

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Create a working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt 

# Copy the entire application
COPY ./Content /app 


ENV HOST_ADDRESS=0.0.0.0
ENV HOST_PORT=6662
ENV SERVICE_NAME="Extractor"

# Expose the Flask port
EXPOSE $HOST_PORT

# Define the command to run your Flask app with the development server
CMD ["python", "app.py"]