"""MCP tools for SD-WAN certificate management"""

import logging
from typing import Any, Dict, List
from datetime import datetime
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


def list_certificates() -> Dict[str, Any]:
    """
    List all device certificates

    Returns:
        {
          "success": bool,
          "certificate_count": int,
          "certificates": [
            {
              "cn": str,
              "issuer": str,
              "validity": str,
              "expiry_date": str,
              "days_to_expiry": int
            }
          ]
        }
    """
    try:
        client = get_vmanage_client()
        certs = client.get_certificates()

        now = datetime.utcnow()
        cert_list = []

        for cert in certs:
            cn = cert.get("cn") or cert.get("common_name", "")
            expiry_str = cert.get("expiry_date") or cert.get("not_after", "")
            days_to_expiry = 0

            try:
                if expiry_str:
                    expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                    days_to_expiry = (expiry - now).days
            except:
                pass

            cert_list.append({
                "cn": cn,
                "issuer": cert.get("issuer", ""),
                "validity": cert.get("validity", ""),
                "expiry_date": expiry_str,
                "days_to_expiry": days_to_expiry,
                "serial_number": cert.get("serial_number", "")
            })

        return {
            "success": True,
            "certificate_count": len(cert_list),
            "certificates": cert_list
        }
    except Exception as e:
        logger.error(f"Failed to list certificates: {e}")
        return {
            "success": False,
            "error": str(e),
            "certificate_count": 0,
            "certificates": []
        }


def get_expiring_certs(days_warning: int = 30) -> Dict[str, Any]:
    """
    Get certificates expiring within specified days

    Args:
        days_warning: Number of days for expiry warning

    Returns:
        {
          "success": bool,
          "expiring_count": int,
          "expired_count": int,
          "expiring_soon": [...],
          "expired": [...]
        }
    """
    try:
        client = get_vmanage_client()
        certs = client.get_certificates()

        now = datetime.utcnow()
        expiring_soon = []
        expired = []

        for cert in certs:
            cn = cert.get("cn") or cert.get("common_name", "")
            expiry_str = cert.get("expiry_date") or cert.get("not_after", "")

            if not expiry_str:
                continue

            try:
                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                days_to_expiry = (expiry - now).days

                if days_to_expiry < 0:
                    expired.append({
                        "cn": cn,
                        "expiry_date": expiry_str,
                        "days_overdue": abs(days_to_expiry)
                    })
                elif days_to_expiry < days_warning:
                    expiring_soon.append({
                        "cn": cn,
                        "expiry_date": expiry_str,
                        "days_to_expiry": days_to_expiry
                    })
            except:
                pass

        return {
            "success": True,
            "expiring_count": len(expiring_soon),
            "expired_count": len(expired),
            "days_warning": days_warning,
            "expiring_soon": expiring_soon,
            "expired": expired
        }
    except Exception as e:
        logger.error(f"Failed to get expiring certs: {e}")
        return {
            "success": False,
            "error": str(e),
            "expiring_count": 0,
            "expired_count": 0,
            "expiring_soon": [],
            "expired": []
        }


def check_root_ca() -> Dict[str, Any]:
    """
    Check root CA certificate status

    Returns:
        {
          "success": bool,
          "root_ca_status": str,
          "root_ca_cert": {...}
        }
    """
    try:
        client = get_vmanage_client()
        certs = client.get_certificates()

        # Look for root CA certificate
        root_ca = next((c for c in certs if "root" in c.get("cn", "").lower() or "ca" in c.get("cn", "").lower()), None)

        if not root_ca:
            return {
                "success": False,
                "error": "Root CA certificate not found"
            }

        now = datetime.utcnow()
        expiry_str = root_ca.get("expiry_date") or root_ca.get("not_after", "")
        days_to_expiry = 0

        try:
            if expiry_str:
                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                days_to_expiry = (expiry - now).days
        except:
            pass

        status = "EXPIRED" if days_to_expiry < 0 else "EXPIRING_SOON" if days_to_expiry < 90 else "HEALTHY"

        return {
            "success": True,
            "root_ca_status": status,
            "root_ca_cert": {
                "cn": root_ca.get("cn", ""),
                "issuer": root_ca.get("issuer", ""),
                "expiry_date": expiry_str,
                "days_to_expiry": days_to_expiry,
                "validity": root_ca.get("validity", "")
            }
        }
    except Exception as e:
        logger.error(f"Failed to check root CA: {e}")
        return {
            "success": False,
            "error": str(e)
        }
