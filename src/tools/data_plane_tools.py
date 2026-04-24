"""MCP tools for SD-WAN data plane operations"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient
from ..config import get_settings
from ..analyzers.bfd_analyzer import BFDAnalyzer

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


def get_bfd_sessions(device_id: str = None) -> Dict[str, Any]:
    """
    Get BFD session status across fabric or for specific device

    Returns session state (up/down), loss percentage, latency, jitter, color

    Args:
        device_id: Optional device ID to filter (e.g., "device-uuid")

    Returns:
        {
          "success": bool,
          "total_sessions": int,
          "up_sessions": int,
          "down_sessions": int,
          "by_color": {...},
          "sessions": [...],
          "analysis": {...}
        }
    """
    try:
        client = get_vmanage_client()
        sessions = client.get_bfd_sessions(device_id=device_id)

        # Analyze sessions
        analysis = BFDAnalyzer.analyze_bfd_sessions(sessions)

        return {
            "success": True,
            "total_sessions": len(sessions),
            "up_sessions": sum(1 for s in sessions if s.get("state", "").lower() == "up"),
            "down_sessions": sum(1 for s in sessions if s.get("state", "").lower() != "up"),
            "by_color": analysis.get("by_color", {}),
            "sessions": sessions[:50],
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to get BFD sessions: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_sessions": 0,
            "sessions": []
        }


def get_tunnel_stats(device_id: str = None) -> Dict[str, Any]:
    """
    Get IPsec tunnel statistics (packet counts, throughput)

    Args:
        device_id: Optional device ID to filter

    Returns:
        {
          "success": bool,
          "tunnel_count": int,
          "tunnels": [...]
        }
    """
    try:
        client = get_vmanage_client()
        # Note: This endpoint may vary by vManage version
        # Using BFD as proxy for tunnel status
        sessions = client.get_bfd_sessions(device_id=device_id)

        tunnels = [
            {
                "tunnel_id": f"{s.get('src_ip', '')}-{s.get('dst_ip', '')}",
                "source": s.get("src_ip") or s.get("local_ip", ""),
                "destination": s.get("dst_ip") or s.get("remote_ip", ""),
                "color": s.get("color", ""),
                "state": s.get("state", ""),
                "loss_pct": float(s.get("loss_percentage", 0) or 0),
                "latency_ms": float(s.get("latency", 0) or 0),
                "jitter_ms": float(s.get("jitter", 0) or 0)
            }
            for s in sessions
        ]

        return {
            "success": True,
            "tunnel_count": len(tunnels),
            "tunnels": tunnels[:50]
        }
    except Exception as e:
        logger.error(f"Failed to get tunnel stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "tunnel_count": 0,
            "tunnels": []
        }


def check_tloc_status(device_id: str = None) -> Dict[str, Any]:
    """
    Check TLOC (Transport Locator) status across fabric

    Returns TLOC list with system-ip, color, encapsulation, and status

    Args:
        device_id: Optional device ID to filter

    Returns:
        {
          "success": bool,
          "tloc_count": int,
          "up_tlocs": int,
          "down_tlocs": int,
          "tlocs": [...]
        }
    """
    try:
        client = get_vmanage_client()
        tlocs = client.get_omp_tlocs(device_id=device_id)

        up_count = 0
        down_count = 0

        tloc_list = []
        for tloc in tlocs:
            status = tloc.get("state", "").lower()
            if status == "up":
                up_count += 1
            else:
                down_count += 1

            tloc_list.append({
                "system_ip": tloc.get("system_ip") or tloc.get("systemIp", ""),
                "color": tloc.get("color", ""),
                "encapsulation": tloc.get("encapsulation", ""),
                "state": status,
                "preference": tloc.get("preference", ""),
                "weight": tloc.get("weight", ""),
                "public_ip": tloc.get("public_ip", "")
            })

        return {
            "success": True,
            "tloc_count": len(tloc_list),
            "up_tlocs": up_count,
            "down_tlocs": down_count,
            "tlocs": tloc_list[:50]
        }
    except Exception as e:
        logger.error(f"Failed to check TLOC status: {e}")
        return {
            "success": False,
            "error": str(e),
            "tloc_count": 0,
            "tlocs": []
        }


def get_app_route_stats(vpn_id: int = 0) -> Dict[str, Any]:
    """
    Get application-aware routing (AAR) route statistics

    Args:
        vpn_id: VPN ID to filter (default 0 for transport VPN)

    Returns:
        {
          "success": bool,
          "route_count": int,
          "routes": [...]
        }
    """
    try:
        client = get_vmanage_client()
        routes = client.get_omp_routes(vpn=vpn_id)

        route_list = [
            {
                "prefix": route.get("prefix") or route.get("route", ""),
                "type": route.get("type", ""),
                "originator": route.get("originator", ""),
                "preference": route.get("preference", ""),
                "tag": route.get("tag", ""),
                "pathid": route.get("pathid", ""),
                "metric": route.get("metric", "")
            }
            for route in routes
        ]

        return {
            "success": True,
            "vpn_id": vpn_id,
            "route_count": len(route_list),
            "routes": route_list[:50]
        }
    except Exception as e:
        logger.error(f"Failed to get app route stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "vpn_id": vpn_id,
            "route_count": 0,
            "routes": []
        }
