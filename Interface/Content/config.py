import os

class Config:
    HOST_ADDRESS = os.getenv("HOST_ADDRESS", "0.0.0.0")
    HOST_PORT = os.getenv("HOST_PORT", "6660")
    SERVICE_NAME = os.getenv("SERVICE_NAME","Interface")

    SIMULATOR_ADDRESS = os.getenv("SIMULATOR_ADDRESS", "0.0.0.0")
    SIMULATOR_PORT = os.getenv("SIMULATOR_PORT", "6661")