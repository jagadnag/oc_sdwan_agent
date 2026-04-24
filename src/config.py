"""Configuration management for SD-WAN AI Agent"""

import os
import logging
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file"""

    # vManage REST API Configuration
    vmanage_host: str = Field(..., description="vManage IP address or hostname")
    vmanage_port: int = Field(default=443, description="vManage HTTPS port")
    vmanage_user: str = Field(..., description="vManage administrative username")
    vmanage_password: str = Field(..., description="vManage administrative password")
    vmanage_verify_ssl: bool = Field(default=False, description="Verify SSL certificates (disable for lab)")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field(
        default="%(asctime)s %(levelname)s %(name)s: %(message)s",
        description="Log message format"
    )

    # Optional: Default Controller
    default_controller: Optional[str] = Field(default="prod-manager", description="Default controller from controllers.csv")

    # MCP Server Configuration
    mcp_host: str = Field(default="localhost", description="MCP server host")
    mcp_port: int = Field(default=4000, description="MCP server port")

    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching of API responses")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")

    # API Timeout
    api_timeout: int = Field(default=30, description="API request timeout in seconds")

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_required_fields(self) -> None:
        """Validate that required fields are set"""
        required = ["vmanage_host", "vmanage_user", "vmanage_password"]
        missing = [field for field in required if not getattr(self, field)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


def setup_logging(level: str = "INFO", name: str = "sdwan_agent") -> logging.Logger:
    """Configure logging for the application"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with formatted output
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    # Only add handler if not already present (avoid duplicates)
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


def get_settings() -> Settings:
    """Get application settings, with validation"""
    try:
        settings = Settings()
        settings.validate_required_fields()
        return settings
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")


# Global settings instance
settings = get_settings()

# Configure logging
logger = setup_logging(settings.log_level)
