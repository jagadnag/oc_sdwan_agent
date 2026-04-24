"""SD-WAN AI Operations Agent - Python Package"""

__version__ = "1.0.0"
__author__ = "Cisco SD-WAN AI Agent"
__description__ = "Production-grade SD-WAN AI operations and troubleshooting assistant"

from .config import settings
from .vmanage_client import VManageClient
from .sdwan_collector import SDWANCollector
from .sdwan_analyzer import SDWANAnalyzer

__all__ = [
    "settings",
    "VManageClient",
    "SDWANCollector",
    "SDWANAnalyzer",
]
