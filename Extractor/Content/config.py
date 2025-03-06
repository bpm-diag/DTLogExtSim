import os

class Config:
    HOST_ADDRESS = os.getenv("HOST_ADDRESS", "0.0.0.0")
    HOST_PORT = os.getenv("HOST_PORT", "6662")
    SERVICE_NAME = os.getenv("SERVICE_NAME","Extractor")