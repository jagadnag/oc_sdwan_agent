"""MCP tools for SD-WAN upgrade and software management"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient
from ..config import get_settings

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


def list_software_versions() -> Dict[str, Any]:
    """
    List software versions across all devices

    Returns:
        {
          "success": bool,
          "total_devices": int,
          "version_distribution": {...},
          "devices_by_version": {...}
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()

        version_dist = {}
        devices_by_version = {}

        for device in devices:
            version = device.get("softwareVersion") or device.get("version", "unknown")
            hostname = device.get("hostName") or device.get("hostname", "")

            # Version distribution count
            version_dist[version] = version_dist.get(version, 0) + 1

            # Devices by version
            if version not in devices_by_version:
                devices_by_version[version] = []
            devices_by_version[version].append({
                "hostname": hostname,
                "device_id": device.get("deviceId") or device.get("uuid", ""),
                "device_type": device.get("deviceType", "")
            })

        return {
            "success": True,
            "total_devices": len(devices),
            "version_distribution": version_dist,
            "devices_by_version": devices_by_version
        }
    except Exception as e:
        logger.error(f"Failed to list software versions: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_devices": 0,
            "version_distribution": {}
        }


def get_compliance_status(target_version: str) -> Dict[str, Any]:
    """
    Check software version compliance against target version

    Args:
        target_version: Target software version (e.g., "20.12.4")

    Returns:
        {
          "success": bool,
          "total_devices": int,
          "compliant_devices": int,
          "non_compliant_devices": int,
          "compliance_percent": float,
          "non_compliant": [...]
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()

        compliant = []
        non_compliant = []

        for device in devices:
            version = device.get("softwareVersion") or device.get("version", "unknown")
            hostname = device.get("hostName") or device.get("hostname", "")
            device_id = device.get("deviceId") or device.get("uuid", "")

            if version == target_version:
                compliant.append(hostname)
            else:
                non_compliant.append({
                    "hostname": hostname,
                    "device_id": device_id,
                    "current_version": version,
                    "target_version": target_version,
                    "device_type": device.get("deviceType", "")
                })

        total = len(devices)
        compliance = (len(compliant) / total * 100) if total > 0 else 0

        return {
            "success": True,
            "total_devices": total,
            "compliant_devices": len(compliant),
            "non_compliant_devices": len(non_compliant),
            "compliance_percent": round(compliance, 1),
            "target_version": target_version,
            "non_compliant": non_compliant[:50]
        }
    except Exception as e:
        logger.error(f"Failed to get compliance status: {e}")
        return {
            "success": False,
            "error": str(e),
            "target_version": target_version,
            "total_devices": 0,
            "compliance_percent": 0
        }


def plan_software_upgrade(target_version: str, device_filter: str = None) -> Dict[str, Any]:
    """
    Plan software upgrade with staged approach

    Args:
        target_version: Target software version
        device_filter: Optional filter (e.g., "vedges" or "controllers")

    Returns:
        {
          "success": bool,
          "upgrade_stages": [...],
          "estimated_duration_hours": float,
          "risk_level": str,
          "recommendations": [...]
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()

        # Filter devices
        if device_filter == "vedges":
            devices = [d for d in devices if "vedge" in d.get("deviceType", "").lower()]
        elif device_filter == "controllers":
            devices = [d for d in devices if "vsmart" in d.get("deviceType", "").lower() or "vmanage" in d.get("deviceType", "").lower()]

        # Separate by type
        vedges = [d for d in devices if "vedge" in d.get("deviceType", "").lower()]
        controllers = [d for d in devices if "vsmart" in d.get("deviceType", "").lower() or "vmanage" in d.get("deviceType", "").lower()]

        # Create upgrade stages
        stages = []

        if controllers:
            stages.append({
                "stage": 1,
                "name": "Controller Upgrade",
                "device_count": len(controllers),
                "duration_hours": len(controllers) * 0.5,
                "devices": [d.get("hostName") or d.get("hostname", "") for d in controllers][:5]
            })

        # Batch vedges in groups of 10
        batch_size = 10
        for i in range(0, len(vedges), batch_size):
            batch = vedges[i:i+batch_size]
            stages.append({
                "stage": len(stages) + 1,
                "name": f"Edge Batch {len(stages)} ({len(batch)} devices)",
                "device_count": len(batch),
                "duration_hours": len(batch) * 0.25,
                "devices": [d.get("hostName") or d.get("hostname", "") for d in batch][:3]
            })

        total_duration = sum(s["duration_hours"] for s in stages)

        return {
            "success": True,
            "target_version": target_version,
            "devices_to_upgrade": len(devices),
            "upgrade_stages": stages,
            "estimated_duration_hours": round(total_duration, 1),
            "risk_level": "MEDIUM",
            "recommendations": [
                "Backup configurations before upgrade",
                "Perform upgrade during maintenance window",
                "Monitor BFD and control plane during upgrade",
                "Have rollback plan ready",
                "Upgrade controllers before edges"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to plan upgrade: {e}")
        return {
            "success": False,
            "error": str(e),
            "target_version": target_version
        }
