"""
Configuration settings for MATPOWER Web Backend
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration"""

    # MATPOWER Configuration
    MATPOWER_PATH: str = "E:/matpower"
    MATPOWER_DATA_PATH: str = "E:/matpower/data"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Octave Configuration
    OCTAVE_TIMEOUT: int = 60  # seconds
    OCTAVE_PATH: str = "octave"  # Path to octave executable

    # CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176"
    ]

    # Simulation Configuration
    MAX_SIMULATION_TIME: int = 300  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_matpower_path() -> Path:
    """Get MATPOWER installation path"""
    return Path(settings.MATPOWER_PATH)


def get_data_path() -> Path:
    """Get MATPOWER data directory path"""
    return Path(settings.MATPOWER_DATA_PATH)
