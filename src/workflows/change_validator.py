"""Pre/post change validation snapshots"""

import logging
from datetime import datetime
from typing import Any, Dict
from ..vmanage_client import VManageClient
from ..collector import SDWANCollector

logger = logging.getLogger(__name__)


def take_pre_change_snapshot(client: VManageClient, change_name: str) -> Dict[str, Any]:
    """
    Take pre-change baseline snapshot for validation

    Args:
        client: Authenticated VManageClient instance
        change_name: Name/description of planned change

    Returns:
        {
          "snapshot_id": str,
          "timestamp": ISO string,
          "change_name": str,
          "snapshot_type": "pre_change",
          "data": {baseline metrics}
        }
    """
    logger.info(f"Taking pre-change snapshot for: {change_name}")

    snapshot_id = f"snapshot-pre-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.utcnow().isoformat() + "Z"

    try:
        collector = SDWANCollector(client)
        snapshot = collector.collect_full_health_snapshot()

        return {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "change_name": change_name,
            "snapshot_type": "pre_change",
            "data": snapshot
        }

    except Exception as e:
        logger.error(f"Pre-change snapshot failed: {e}")
        return {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "change_name": change_name,
            "error": str(e)
        }


def take_post_change_snapshot(client: VManageClient, change_name: str) -> Dict[str, Any]:
    """
    Take post-change snapshot for comparison

    Args:
        client: Authenticated VManageClient instance
        change_name: Name/description of change performed

    Returns:
        {
          "snapshot_id": str,
          "timestamp": ISO string,
          "change_name": str,
          "snapshot_type": "post_change",
          "data": {baseline metrics}
        }
    """
    logger.info(f"Taking post-change snapshot for: {change_name}")

    snapshot_id = f"snapshot-post-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.utcnow().isoformat() + "Z"

    try:
        collector = SDWANCollector(client)
        snapshot = collector.collect_full_health_snapshot()

        return {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "change_name": change_name,
            "snapshot_type": "post_change",
            "data": snapshot
        }

    except Exception as e:
        logger.error(f"Post-change snapshot failed: {e}")
        return {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "change_name": change_name,
            "error": str(e)
        }


def compare_snapshots(pre_snapshot: Dict[str, Any], post_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare pre and post snapshots to validate change

    Args:
        pre_snapshot: Pre-change snapshot dict
        post_snapshot: Post-change snapshot dict

    Returns:
        {
          "change_name": str,
          "validation_status": "PASS" | "FAIL" | "DEGRADED",
          "comparison": {
            "fabric": {...},
            "control_plane": {...},
            "data_plane": {...}
          },
          "issues_detected": [...],
          "recommendations": [...]
        }
    """
    logger.info(f"Comparing snapshots for {pre_snapshot.get('change_name')}")

    pre = pre_snapshot.get("data", {})
    post = post_snapshot.get("data", {})
    issues = []

    # Compare fabric metrics
    pre_fabric = pre.get("fabric", {})
    post_fabric = post.get("fabric", {})

    pre_reachable = pre_fabric.get("reachable_count", 0)
    post_reachable = post_fabric.get("reachable_count", 0)

    if post_reachable < pre_reachable:
        issues.append({
            "category": "fabric",
            "issue": f"Device reachability decreased: {pre_reachable} -> {post_reachable}",
            "severity": "HIGH"
        })

    # Compare control plane
    pre_control = pre.get("control_plane", {})
    post_control = post.get("control_plane", {})

    pre_ctrl_up = pre_control.get("healthy_connections", 0)
    post_ctrl_up = post_control.get("healthy_connections", 0)

    if post_ctrl_up < pre_ctrl_up:
        issues.append({
            "category": "control_plane",
            "issue": f"Control connections down: {pre_ctrl_up} -> {post_ctrl_up}",
            "severity": "HIGH"
        })

    # Compare data plane
    pre_data = pre.get("data_plane", {})
    post_data = post.get("data_plane", {})

    pre_bfd_up = pre_data.get("up_sessions", 0)
    post_bfd_up = post_data.get("up_sessions", 0)

    if post_bfd_up < pre_bfd_up:
        issues.append({
            "category": "data_plane",
            "issue": f"BFD sessions down: {pre_bfd_up} -> {post_bfd_up}",
            "severity": "HIGH"
        })

    pre_flapping = pre_data.get("flapping_sessions", 0)
    post_flapping = post_data.get("flapping_sessions", 0)

    if post_flapping > pre_flapping:
        issues.append({
            "category": "data_plane",
            "issue": f"Flapping sessions increased: {pre_flapping} -> {post_flapping}",
            "severity": "MEDIUM"
        })

    # Compare alarms
    pre_alarms = pre.get("alarms", {})
    post_alarms = post.get("alarms", {})

    pre_critical = pre_alarms.get("critical_count", 0)
    post_critical = post_alarms.get("critical_count", 0)

    if post_critical > pre_critical:
        issues.append({
            "category": "alarms",
            "issue": f"Critical alarms increased: {pre_critical} -> {post_critical}",
            "severity": "HIGH"
        })

    # Determine validation status
    if not issues:
        validation_status = "PASS"
    elif any(i["severity"] == "HIGH" for i in issues):
        validation_status = "FAIL"
    else:
        validation_status = "DEGRADED"

    return {
        "change_name": pre_snapshot.get("change_name", "unknown"),
        "pre_snapshot_id": pre_snapshot.get("snapshot_id"),
        "post_snapshot_id": post_snapshot.get("snapshot_id"),
        "validation_status": validation_status,
        "comparison": {
            "fabric": {
                "pre_reachable": pre_reachable,
                "post_reachable": post_reachable,
                "delta": post_reachable - pre_reachable
            },
            "control_plane": {
                "pre_up": pre_ctrl_up,
                "post_up": post_ctrl_up,
                "delta": post_ctrl_up - pre_ctrl_up
            },
            "data_plane": {
                "pre_bfd_up": pre_bfd_up,
                "post_bfd_up": post_bfd_up,
                "delta": post_bfd_up - pre_bfd_up,
                "pre_flapping": pre_flapping,
                "post_flapping": post_flapping,
                "flap_delta": post_flapping - pre_flapping
            }
        },
        "issues_detected": issues,
        "recommendations": _generate_validation_recommendations(validation_status, issues)
    }


def _generate_validation_recommendations(status: str, issues: list) -> list:
    """Generate recommendations based on validation results"""
    recommendations = []

    if status == "PASS":
        recommendations.append("Change validation PASSED - no anomalies detected")
    elif status == "DEGRADED":
        recommendations.append("Change validation DEGRADED - minor issues detected, monitor closely")
        for issue in issues:
            if issue["category"] == "data_plane":
                recommendations.append("Monitor BFD session stability and tunnel flapping")
    elif status == "FAIL":
        recommendations.append("Change validation FAILED - rollback recommended")
        recommendations.append("Investigate detected issues before proceeding")

    return recommendations
