"""MCP tools for SD-WAN alarm and monitoring operations"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient
from ..config import get_settings
from ..analyzers.alarm_correlator import AlarmCorrelator

logger = logging.getLogger(__name__)


def get_vmanage_client() -> VManageClient:
    """Get authenticated vManage client"""
    settings = get_settings()
    client = VManageClient(
        host=settings.vmanage_host,
        port=settings.vmanage_port,
        user=settings.vmanage_user,
        password=settings.vmanage_password,
        verify_ssl=settings.vmanage_verify_ssl,
        timeout=settings.api_timeout
    )
    client.authenticate()
    return client


def list_alarms(severity: str = None, limit: int = 50) -> Dict[str, Any]:
    """
    List all alarms with optional severity filtering

    Args:
        severity: Optional severity filter (critical, major, minor)
        limit: Maximum number of alarms to return

    Returns:
        {
          "success": bool,
          "total_alarms": int,
          "alarms": [...],
          "severity_breakdown": {...}
        }
    """
    try:
        client = get_vmanage_client()
        query = {}
        if severity:
            query["severity"] = severity.lower()

        alarms = client.get_alarms(query=query)

        severity_breakdown = {
            "critical": sum(1 for a in alarms if a.get("severity", "").lower() == "critical"),
            "major": sum(1 for a in alarms if a.get("severity", "").lower() == "major"),
            "minor": sum(1 for a in alarms if a.get("severity", "").lower() == "minor")
        }

        return {
            "success": True,
            "total_alarms": len(alarms),
            "alarms": alarms[:limit],
            "severity_breakdown": severity_breakdown
        }
    except Exception as e:
        logger.error(f"Failed to list alarms: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_alarms": 0,
            "alarms": []
        }


def get_alarms_24h(severity: str = None) -> Dict[str, Any]:
    """
    Get alarms from last 24 hours

    Args:
        severity: Optional severity filter

    Returns:
        {
          "success": bool,
          "alarms_24h": int,
          "alarms": [...],
          "top_types": [...]
        }
    """
    try:
        client = get_vmanage_client()
        query = {}
        if severity:
            query["severity"] = severity.lower()

        alarms = client.get_alarms(query=query)

        # Get top alarm types
        top_types = AlarmCorrelator.top_alarm_types(alarms, limit=5)

        return {
            "success": True,
            "alarms_24h": len(alarms),
            "alarms": alarms[:50],
            "top_alarm_types": top_types,
            "severity_breakdown": {
                "critical": sum(1 for a in alarms if a.get("severity", "").lower() == "critical"),
                "major": sum(1 for a in alarms if a.get("severity", "").lower() == "major"),
                "minor": sum(1 for a in alarms if a.get("severity", "").lower() == "minor")
            }
        }
    except Exception as e:
        logger.error(f"Failed to get 24h alarms: {e}")
        return {
            "success": False,
            "error": str(e),
            "alarms_24h": 0,
            "alarms": []
        }


def correlate_alarms(time_window_min: int = 30) -> Dict[str, Any]:
    """
    Correlate alarms to detect patterns and root causes

    Args:
        time_window_min: Time window in minutes for correlation

    Returns:
        {
          "success": bool,
          "root_cause_candidates": [...],
          "thundering_herd": bool,
          "correlation": {...}
        }
    """
    try:
        client = get_vmanage_client()
        alarms = client.get_alarms()

        correlator = AlarmCorrelator()
        correlation = correlator.correlate(alarms, time_window_min=time_window_min)

        return {
            "success": True,
            "root_cause_candidates": correlation.get("root_cause_candidates", []),
            "thundering_herd": correlation.get("thundering_herd", False),
            "correlation": correlation
        }
    except Exception as e:
        logger.error(f"Failed to correlate alarms: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_active_alarms() -> Dict[str, Any]:
    """
    Get currently active alarms (uncleared)

    Returns:
        {
          "success": bool,
          "active_alarm_count": int,
          "alarms": [...]
        }
    """
    try:
        client = get_vmanage_client()
        alarms = client.get_alarms()

        # Filter active (not cleared)
        active = [a for a in alarms if a.get("cleared", False) != True]

        critical_count = sum(1 for a in active if a.get("severity", "").lower() == "critical")
        major_count = sum(1 for a in active if a.get("severity", "").lower() == "major")

        return {
            "success": True,
            "active_alarm_count": len(active),
            "critical_count": critical_count,
            "major_count": major_count,
            "alarms": active[:50]
        }
    except Exception as e:
        logger.error(f"Failed to get active alarms: {e}")
        return {
            "success": False,
            "error": str(e),
            "active_alarm_count": 0,
            "alarms": []
        }
