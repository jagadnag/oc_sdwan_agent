"""MCP tools for SD-WAN control plane operations"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient
from ..config import get_settings
from ..analyzers.control_analyzer import ControlPlaneAnalyzer

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


def get_control_connections(device_id: str = None) -> Dict[str, Any]:
    """
    Get control plane connections (device to vManage/vSmart)

    Returns established and down connections with peer addresses and protocol

    Args:
        device_id: Optional device ID to filter

    Returns:
        {
          "success": bool,
          "total_connections": int,
          "up_connections": int,
          "down_connections": int,
          "vsmart_count": int,
          "vmanage_count": int,
          "connections": [...],
          "analysis": {...}
        }
    """
    try:
        client = get_vmanage_client()
        connections = client.get_control_connections()

        if device_id:
            connections = [c for c in connections if c.get("device_id") == device_id]

        # Analyze connections
        analysis = ControlPlaneAnalyzer.analyze_control_connections(connections)

        return {
            "success": True,
            "total_connections": len(connections),
            "up_connections": sum(1 for c in connections if c.get("state", "").lower() == "up"),
            "down_connections": sum(1 for c in connections if c.get("state", "").lower() != "up"),
            "vsmart_count": analysis.get("vsmart_count", 0),
            "vmanage_count": analysis.get("vmanage_count", 0),
            "dtls_up": analysis.get("dtls_up", 0),
            "tls_up": analysis.get("tls_up", 0),
            "connections": connections[:50],
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to get control connections: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_connections": 0,
            "connections": []
        }


def check_omp_peers(device_id: str = None) -> Dict[str, Any]:
    """
    Check OMP (Overlay Management Protocol) peer status

    Returns peer establishment state, routes received, and peer health

    Args:
        device_id: Optional device ID to filter

    Returns:
        {
          "success": bool,
          "total_peers": int,
          "established_peers": int,
          "down_peers": int,
          "peers": [...],
          "analysis": {...}
        }
    """
    try:
        client = get_vmanage_client()
        peers = client.get_omp_peers(device_id=device_id)

        # Analyze OMP peers
        analysis = ControlPlaneAnalyzer.analyze_omp_peers(peers)

        return {
            "success": True,
            "total_peers": len(peers),
            "established_peers": analysis.get("established_count", 0),
            "down_peers": analysis.get("down_count", 0),
            "avg_routes_per_peer": analysis.get("avg_routes_per_peer", 0),
            "peers": peers[:50],
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to check OMP peers: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_peers": 0,
            "peers": []
        }


def get_vsmart_status() -> Dict[str, Any]:
    """
    Get vSmart controller status across fabric

    Returns vSmart controller list with connectivity and OMP establishment state

    Returns:
        {
          "success": bool,
          "vsmart_count": int,
          "active_count": int,
          "vsmart_controllers": [...],
          "redundancy_status": str
        }
    """
    try:
        client = get_vmanage_client()
        devices = client.get_devices()
        vsmart_devices = [
            d for d in devices
            if "vsmart" in d.get("deviceType", "").lower()
        ]

        connections = client.get_control_connections()
        vsmart_conns = [c for c in connections if "vsmart" in c.get("peer_type", "").lower()]
        active_count = sum(1 for c in vsmart_conns if c.get("state", "").lower() == "up")

        vsmart_list = [
            {
                "hostname": d.get("hostName") or d.get("hostname", ""),
                "system_ip": d.get("systemIp") or d.get("system_ip", ""),
                "device_id": d.get("deviceId") or d.get("uuid", ""),
                "software_version": d.get("softwareVersion", ""),
                "reachability": d.get("reachability", "unknown"),
                "peers_connected": sum(
                    1 for c in vsmart_conns
                    if c.get("peer_ip") == d.get("systemIp")
                    and c.get("state", "").lower() == "up"
                )
            }
            for d in vsmart_devices
        ]

        redundancy = "HEALTHY" if active_count >= 2 else "DEGRADED" if active_count == 1 else "FAILED"

        return {
            "success": True,
            "vsmart_count": len(vsmart_devices),
            "active_count": active_count,
            "vsmart_controllers": vsmart_list,
            "redundancy_status": redundancy
        }
    except Exception as e:
        logger.error(f"Failed to get vSmart status: {e}")
        return {
            "success": False,
            "error": str(e),
            "vsmart_count": 0,
            "vsmart_controllers": []
        }
