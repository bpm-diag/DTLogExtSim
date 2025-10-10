import os

class Config:
    HOST_ADDRESS = os.getenv("HOST_ADDRESS", "0.0.0.0")
    HOST_PORT = os.getenv("HOST_PORT", "6660")
    SERVICE_NAME = os.getenv("SERVICE_NAME","Interface")

    SIMULATOR_ADDRESS = os.getenv("SIMULATOR_ADDRESS", "0.0.0.0")
    SIMULATOR_PORT = os.getenv("SIMULATOR_PORT", "6661")

    EXTRACTOR_ADDRESS = os.getenv("EXTRACTOR_ADDRESS", "0.0.0.0")
    EXTRACTOR_PORT = os.getenv("EXTRACTOR_PORT", "6662")
    # What-If service (API Flask) e UI (Next.js)
    WHATIF_API_URL = os.getenv("WHATIF_API_URL", "http://whatif_api:5000")
    WHATIF_UI_URL  = os.getenv("WHATIF_UI_URL",  "http://localhost:3003")
