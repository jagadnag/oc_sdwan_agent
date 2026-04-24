"""MCP tools for SD-WAN inventory operations"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient
from ..config import get_settings
from ..inventory import ControllerInventory

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


def list_devices() -> Dict[str, Any]:
    """
    List all WAN edge devices in fabric

    Returns device list with ID, hostname, model, site ID, reachability, and software version

    Returns:
        {
          "success": bool,
          "device_count": int,
          "devices": [
            {
              "device_id": str,
              "hostname": str,
              "model": str,
              "site_id": str,
              "reachability": str,
              "software_version": str,
              "device_type": str,
              "system_ip": str
            }
          ]
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()

        device_list = []
        for dev in devices:
            device_list.append({
                "device_id": dev.get("deviceId") or dev.get("uuid", ""),
                "hostname": dev.get("hostName") or dev.get("hostname", ""),
                "model": dev.get("deviceModel") or dev.get("model", ""),
                "site_id": dev.get("site-id") or dev.get("siteId", ""),
                "reachability": dev.get("reachability", "unknown"),
                "software_version": dev.get("softwareVersion") or dev.get("version", ""),
                "device_type": dev.get("deviceType") or dev.get("type", ""),
                "system_ip": dev.get("systemIp") or dev.get("system_ip", "")
            })

        return {
            "success": True,
            "device_count": len(device_list),
            "devices": device_list
        }
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_count": 0,
            "devices": []
        }


def list_controllers() -> Dict[str, Any]:
    """
    List all controllers (vManage, vSmart) in fabric

    Returns:
        {
          "success": bool,
          "controller_count": int,
          "controllers": [
            {
              "device_id": str,
              "hostname": str,
              "device_type": str,
              "system_ip": str,
              "reachability": str
            }
          ]
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()

        controllers = [
            {
                "device_id": d.get("deviceId") or d.get("uuid", ""),
                "hostname": d.get("hostName") or d.get("hostname", ""),
                "device_type": d.get("deviceType") or d.get("type", ""),
                "system_ip": d.get("systemIp") or d.get("system_ip", ""),
                "reachability": d.get("reachability", "unknown")
            }
            for d in devices
            if "vsmart" in d.get("deviceType", "").lower() or "vmanage" in d.get("deviceType", "").lower()
        ]

        return {
            "success": True,
            "controller_count": len(controllers),
            "controllers": controllers
        }
    except Exception as e:
        logger.error(f"Failed to list controllers: {e}")
        return {
            "success": False,
            "error": str(e),
            "controller_count": 0,
            "controllers": []
        }


def get_device_inventory(device_id: str) -> Dict[str, Any]:
    """
    Get detailed inventory for a specific device

    Args:
        device_id: Device ID or UUID

    Returns:
        {
          "success": bool,
          "device": {...device details...},
          "interfaces": [...],
          "certificates": [...],
          "running_config": str
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()
        device = next((d for d in devices if d.get("deviceId") == device_id or d.get("uuid") == device_id), None)

        if not device:
            return {"success": False, "error": f"Device {device_id} not found"}

        # Get interface stats
        interfaces = client.get_interface_stats(device_id)

        # Get certificates
        certificates = client.get_certificates()

        # Get running config
        config = client.get_running_config(device_id)

        return {
            "success": True,
            "device": {
                "device_id": device.get("deviceId") or device.get("uuid"),
                "hostname": device.get("hostName") or device.get("hostname"),
                "model": device.get("deviceModel"),
                "software_version": device.get("softwareVersion"),
                "system_ip": device.get("systemIp")
            },
            "interface_count": len(interfaces),
            "interfaces": interfaces[:10],
            "certificate_count": len(certificates),
            "config_size_bytes": len(config) if config else 0,
            "config": config[:1000] if config else ""  # First 1000 chars
        }
    except Exception as e:
        logger.error(f"Failed to get device inventory: {e}")
        return {"success": False, "error": str(e)}


def get_site_summary(site_id: str) -> Dict[str, Any]:
    """
    Get summary of all devices at a specific site

    Args:
        site_id: Site ID

    Returns:
        {
          "success": bool,
          "site_id": str,
          "device_count": int,
          "devices": [...],
          "device_types": {...},
          "model_distribution": {...}
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()
        site_devices = [
            d for d in devices
            if d.get("site-id") == site_id or d.get("siteId") == site_id
        ]

        device_types = {}
        model_dist = {}

        for dev in site_devices:
            dev_type = dev.get("deviceType", "unknown")
            model = dev.get("deviceModel", "unknown")

            device_types[dev_type] = device_types.get(dev_type, 0) + 1
            model_dist[model] = model_dist.get(model, 0) + 1

        return {
            "success": True,
            "site_id": site_id,
            "device_count": len(site_devices),
            "device_types": device_types,
            "model_distribution": model_dist,
            "devices": [
                {
                    "device_id": d.get("deviceId") or d.get("uuid"),
                    "hostname": d.get("hostName") or d.get("hostname"),
                    "model": d.get("deviceModel"),
                    "type": d.get("deviceType"),
                    "reachability": d.get("reachability")
                }
                for d in site_devices
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get site summary: {e}")
        return {
            "success": False,
            "error": str(e),
            "site_id": site_id
        }
