"""MCP tools for SD-WAN workflow operations"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict
from ..vmanage_client import VManageClient
from ..sastre_runner import SastreRunner
from ..config import get_settings
from ..workflows.morning_health_check import run_morning_health_check
from ..workflows.incident_triage import triage_incident
from ..workflows.upgrade_planner import plan_upgrade
from ..workflows.change_validator import take_pre_change_snapshot, take_post_change_snapshot, compare_snapshots

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


def run_morning_health_check_tool() -> Dict[str, Any]:
    """
    Run comprehensive morning health check workflow

    Returns daily health report with fabric status, control/data plane health,
    alarms, certificate expiry warnings, and risk score

    Returns:
        {
          "timestamp": ISO string,
          "status_summary": {...},
          "controllers": {...},
          "edges": {...},
          "bfd_health": {...},
          "control_plane": {...},
          "alarms_24h": {...},
          "certificates": {...},
          "risk_score": {...},
          "top_actions": [...]
        }
    """
    try:
        client = get_vmanage_client()
        sastre = SastreRunner()
        result = run_morning_health_check(client, sastre)
        return {
            "success": "error" not in result,
            "report": result
        }
    except Exception as e:
        logger.error(f"Morning health check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def run_incident_triage_tool(site_id_or_device: str, time_window_min: int = 60) -> Dict[str, Any]:
    """
    Triage an incident affecting a site or device

    Performs rapid data collection and correlation to identify root cause

    Args:
        site_id_or_device: Site ID or device ID (e.g., "denver-site-1" or "uuid")
        time_window_min: Time window to analyze (default 60 minutes)

    Returns:
        {
          "success": bool,
          "triage_report": {...}
        }
    """
    try:
        client = get_vmanage_client()
        result = triage_incident(client, site_id_or_device, time_window_min)
        return {
            "success": "error" not in result,
            "triage_report": result
        }
    except Exception as e:
        logger.error(f"Incident triage failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def run_upgrade_plan_tool(target_version: str, device_filter: str = None) -> Dict[str, Any]:
    """
    Plan software upgrade with risk assessment

    Args:
        target_version: Target software version (e.g., "20.12.4")
        device_filter: Optional filter ("vedges", "controllers", or None for all)

    Returns:
        {
          "success": bool,
          "upgrade_plan": {...}
        }
    """
    try:
        client = get_vmanage_client()
        filter_dict = None
        if device_filter == "vedges":
            filter_dict = {"device_type": "vedge"}
        elif device_filter == "controllers":
            filter_dict = {"device_type": "vsmart"}

        result = plan_upgrade(client, target_version, device_filter=filter_dict)
        return {
            "success": "error" not in result,
            "upgrade_plan": result
        }
    except Exception as e:
        logger.error(f"Upgrade planning failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def validate_change_snapshot_tool(change_name: str, snapshot_type: str) -> Dict[str, Any]:
    """
    Take change validation snapshot (pre or post)

    Args:
        change_name: Name of the change (e.g., "Policy Update DR Site")
        snapshot_type: "pre" for pre-change, "post" for post-change

    Returns:
        {
          "success": bool,
          "snapshot": {...}
        }
    """
    try:
        client = get_vmanage_client()

        if snapshot_type.lower() == "pre":
            result = take_pre_change_snapshot(client, change_name)
        elif snapshot_type.lower() == "post":
            result = take_post_change_snapshot(client, change_name)
        else:
            return {
                "success": False,
                "error": "snapshot_type must be 'pre' or 'post'"
            }

        return {
            "success": result.get("success", True),
            "snapshot": result
        }
    except Exception as e:
        logger.error(f"Change snapshot failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def compare_change_snapshots_tool(pre_snapshot: Dict, post_snapshot: Dict) -> Dict[str, Any]:
    """
    Compare pre and post change snapshots for validation

    Args:
        pre_snapshot: Pre-change snapshot dictionary
        post_snapshot: Post-change snapshot dictionary

    Returns:
        {
          "success": bool,
          "validation_result": {...}
        }
    """
    try:
        result = compare_snapshots(pre_snapshot, post_snapshot)
        return {
            "success": True,
            "validation_result": result
        }
    except Exception as e:
        logger.error(f"Snapshot comparison failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def run_health_report_tool(alarm_days: int = 1, skip_pull: bool = False) -> Dict[str, Any]:
    """
    One-command Sastre-first health report generation pipeline.

    Steps:
    1) Pull fresh Sastre data (devices, alarms, state, certificates)
    2) Build AI assessment sections
    3) Generate markdown report under ./reports

    Args:
        alarm_days: Alarm lookback days (default 1)
        skip_pull: Reuse existing JSON pulls if True

    Returns:
        {
          "success": bool,
          "report_path": str,
          "message": str
        }
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        cmd = [
            "python",
            "src/generate_health_report.py",
            "--project-dir", ".",
            "--output-dir", "reports",
            "--alarm-days", str(alarm_days)
        ]
        if skip_pull:
            cmd.append("--skip-pull")

        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            report_path = (result.stdout or "").strip().splitlines()[-1] if result.stdout else ""
            return {
                "success": True,
                "report_path": report_path,
                "message": "Health check report generated successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        return {
            "success": False,
            "error": result.stderr or result.stdout,
            "message": "Health check report generation failed"
        }
    except Exception as e:
        logger.error(f"Health report pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Health check report generation failed"
        }
