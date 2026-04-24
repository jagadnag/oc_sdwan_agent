"""MCP tools for SD-WAN policy operations"""

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


def list_centralized_policies() -> Dict[str, Any]:
    """
    List all centralized policies (control policies, data policies, etc.)

    Returns:
        {
          "success": bool,
          "policy_count": int,
          "policies": [
            {
              "policy_id": str,
              "name": str,
              "type": str,
              "status": str,
              "devices_affected": int
            }
          ]
        }
    """
    try:
        client = get_vmanage_client()
        policies = client.get_policy_list()

        policy_list = [
            {
                "policy_id": p.get("policyId") or p.get("id", ""),
                "name": p.get("policyName") or p.get("name", ""),
                "type": p.get("policyType") or p.get("type", ""),
                "status": p.get("status", ""),
                "description": p.get("description", ""),
                "devices_affected": p.get("devicesAffected", 0) or 0
            }
            for p in policies
        ]

        return {
            "success": True,
            "policy_count": len(policy_list),
            "policies": policy_list
        }
    except Exception as e:
        logger.error(f"Failed to list policies: {e}")
        return {
            "success": False,
            "error": str(e),
            "policy_count": 0,
            "policies": []
        }


def get_active_policy() -> Dict[str, Any]:
    """
    Get currently active centralized policy

    Returns:
        {
          "success": bool,
          "active_policy": {...},
          "deployment_status": str,
          "last_updated": str
        }
    """
    try:
        client = get_vmanage_client()
        policies = client.get_policy_list()

        # Find active policy (status == "active")
        active = next((p for p in policies if p.get("status", "").lower() == "active"), None)

        if not active:
            return {
                "success": False,
                "error": "No active policy found"
            }

        return {
            "success": True,
            "active_policy": {
                "policy_id": active.get("policyId") or active.get("id"),
                "name": active.get("policyName") or active.get("name"),
                "type": active.get("policyType") or active.get("type"),
                "description": active.get("description", ""),
                "devices_affected": active.get("devicesAffected", 0)
            },
            "deployment_status": "ACTIVE",
            "last_updated": active.get("lastUpdated", "")
        }
    except Exception as e:
        logger.error(f"Failed to get active policy: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_aar_policy() -> Dict[str, Any]:
    """
    Get application-aware routing (AAR) policy details

    Returns:
        {
          "success": bool,
          "aar_policies": [...]
        }
    """
    try:
        client = get_vmanage_client()
        policies = client.get_policy_list()

        # Filter for AAR-related policies
        aar_policies = [
            {
                "policy_id": p.get("policyId") or p.get("id"),
                "name": p.get("policyName") or p.get("name"),
                "type": p.get("policyType") or p.get("type"),
                "status": p.get("status"),
                "description": p.get("description", "")
            }
            for p in policies
            if "app" in p.get("type", "").lower() or "aar" in p.get("type", "").lower()
        ]

        return {
            "success": True,
            "aar_policy_count": len(aar_policies),
            "aar_policies": aar_policies
        }
    except Exception as e:
        logger.error(f"Failed to get AAR policy: {e}")
        return {
            "success": False,
            "error": str(e),
            "aar_policy_count": 0,
            "aar_policies": []
        }


def get_data_policy() -> Dict[str, Any]:
    """
    Get data policy (traffic engineering) details

    Returns:
        {
          "success": bool,
          "data_policies": [...]
        }
    """
    try:
        client = get_vmanage_client()
        policies = client.get_policy_list()

        # Filter for data policies
        data_policies = [
            {
                "policy_id": p.get("policyId") or p.get("id"),
                "name": p.get("policyName") or p.get("name"),
                "type": p.get("policyType") or p.get("type"),
                "status": p.get("status"),
                "description": p.get("description", "")
            }
            for p in policies
            if "data" in p.get("type", "").lower()
        ]

        return {
            "success": True,
            "data_policy_count": len(data_policies),
            "data_policies": data_policies
        }
    except Exception as e:
        logger.error(f"Failed to get data policy: {e}")
        return {
            "success": False,
            "error": str(e),
            "data_policy_count": 0,
            "data_policies": []
        }
