"""MCP tools for Sastre CLI integration"""

import logging
import os
from typing import Any, Dict, List
from ..sastre_runner import SastreRunner
from ..config import get_settings

logger = logging.getLogger(__name__)


def get_sastre_runner() -> SastreRunner:
    """Get Sastre runner instance"""
    return SastreRunner(sastre_path="sastre-sd-wan", timeout_sec=60, dryrun_default=True)


def sastre_backup(workdir: str = None, backup_name: str = None) -> Dict[str, Any]:
    """
    Backup device configurations using Sastre

    Args:
        workdir: Working directory for backup (default: ./backup)
        backup_name: Optional backup name

    Returns:
        {
          "success": bool,
          "backup_path": str,
          "stdout": str,
          "stderr": str
        }
    """
    try:
        if not workdir:
            workdir = "./backup"

        sastre = get_sastre_runner()
        result = sastre.backup(workdir=workdir, backup_name=backup_name)

        return {
            "success": result.get("success", False),
            "backup_path": result.get("backup_path", workdir),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "message": "Backup completed successfully" if result.get("success") else "Backup failed"
        }
    except Exception as e:
        logger.error(f"Sastre backup failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Backup failed: {str(e)}"
        }


def sastre_inventory() -> Dict[str, Any]:
    """
    Get Sastre inventory information

    Returns:
        {
          "success": bool,
          "inventory_data": str,
          "stdout": str
        }
    """
    try:
        sastre = get_sastre_runner()
        result = sastre.inventory()

        return {
            "success": result.get("success", False),
            "inventory_data": result.get("inventory_data", ""),
            "stdout": result.get("stdout", "")
        }
    except Exception as e:
        logger.error(f"Sastre inventory failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def sastre_attach_dryrun(devices: List[str] = None) -> Dict[str, Any]:
    """
    Dry-run template attach operation (no changes)

    Args:
        devices: Optional list of device IDs to filter

    Returns:
        {
          "success": bool,
          "dryrun": bool,
          "stdout": str,
          "stderr": str
        }
    """
    try:
        sastre = get_sastre_runner()
        result = sastre.attach_template(device_list=devices, dryrun=True)

        return {
            "success": result.get("success", False),
            "dryrun": result.get("dryrun", True),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "message": "Dry-run completed - no changes made"
        }
    except Exception as e:
        logger.error(f"Sastre attach dryrun failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def sastre_transform(config_dir: str = None) -> Dict[str, Any]:
    """
    Transform configuration data

    Args:
        config_dir: Optional config directory

    Returns:
        {
          "success": bool,
          "stdout": str,
          "stderr": str
        }
    """
    try:
        sastre = get_sastre_runner()
        result = sastre.transform(config_dir=config_dir)

        return {
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", "")
        }
    except Exception as e:
        logger.error(f"Sastre transform failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def sastre_list() -> Dict[str, Any]:
    """
    List devices known to Sastre/controller

    Returns:
        {
          "success": bool,
          "device_count": int,
          "devices": [...]
        }
    """
    try:
        sastre = get_sastre_runner()
        result = sastre.list_devices()

        return {
            "success": result.get("success", False),
            "device_count": result.get("device_count", 0),
            "devices": result.get("devices", []),
            "stdout": result.get("stdout", "")
        }
    except Exception as e:
        logger.error(f"Sastre list failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "device_count": 0,
            "devices": []
        }
