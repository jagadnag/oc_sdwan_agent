"""Software upgrade planning workflow"""

import logging
from typing import Any, Dict, List, Optional
from ..vmanage_client import VManageClient

logger = logging.getLogger(__name__)


def plan_upgrade(client: VManageClient,
                 target_version: str,
                 device_filter: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Plan software upgrade with staged approach and risk assessment

    Args:
        client: Authenticated VManageClient instance
        target_version: Target software version (e.g., "20.12.4")
        device_filter: Optional filter dict {"device_type": "vedge", "site_id": "denver"}

    Returns:
        {
          "target_version": str,
          "current_state": {...},
          "upgrade_stages": [...],
          "risk_assessment": {...},
          "estimated_downtime_min": int,
          "recommendations": [...]
        }
    """
    logger.info(f"Planning upgrade to {target_version}")

    try:
        devices = client.get_devices()

        # Filter devices if needed
        if device_filter:
            filtered = devices
            if "device_type" in device_filter:
                filtered = [d for d in filtered if d.get("deviceType") == device_filter["device_type"]]
            if "site_id" in device_filter:
                filtered = [d for d in filtered if d.get("site-id") == device_filter["site_id"] or d.get("siteId") == device_filter["site_id"]]
            devices = filtered

        # Categorize devices
        vedges = [d for d in devices if d.get("deviceType", "").lower() == "vedge"]
        controllers = [d for d in devices if d.get("deviceType", "").lower() in ["vsmart", "vmanage"]]

        # Analyze current state
        current_versions = {}
        for device in devices:
            version = device.get("softwareVersion") or device.get("version", "unknown")
            if version not in current_versions:
                current_versions[version] = 0
            current_versions[version] += 1

        # Create upgrade stages
        stages = _create_upgrade_stages(vedges, controllers, target_version)

        # Risk assessment
        risk = _assess_upgrade_risk(devices, target_version)

        return {
            "target_version": target_version,
            "current_state": {
                "total_devices": len(devices),
                "vedges": len(vedges),
                "controllers": len(controllers),
                "version_distribution": current_versions
            },
            "upgrade_stages": stages,
            "risk_assessment": risk,
            "estimated_downtime_min": len(vedges) * 3,  # ~3 min per device
            "recommendations": [
                "Plan upgrade during maintenance window",
                "Backup current configuration using Sastre before upgrade",
                "Monitor control plane connectivity during vSmart/vManage upgrade",
                "Upgrade vEdges in batches of 5-10 devices per day",
                "Verify BFD sessions restore after each device upgrade"
            ]
        }

    except Exception as e:
        logger.error(f"Upgrade planning failed: {e}")
        return {
            "target_version": target_version,
            "error": str(e)
        }


def _create_upgrade_stages(vedges: List[Dict], controllers: List[Dict],
                           target_version: str) -> List[Dict[str, Any]]:
    """Create staged upgrade plan"""
    stages = []

    # Stage 1: Controllers
    if controllers:
        stages.append({
            "stage": 1,
            "name": "Control Plane Upgrade",
            "devices": len(controllers),
            "device_list": [d.get("hostName") or d.get("hostname", "") for d in controllers][:5],
            "duration_min": len(controllers) * 5,
            "criticality": "HIGH",
            "notes": "Upgrade vSmart first, then vManage"
        })

    # Stage 2: Edge devices in batches
    batch_size = 10
    for i in range(0, len(vedges), batch_size):
        batch = vedges[i:i+batch_size]
        stages.append({
            "stage": len(stages) + 1,
            "name": f"Edge Batch {len(stages)} ({len(batch)} devices)",
            "devices": len(batch),
            "device_list": [d.get("hostName") or d.get("hostname", "") for d in batch][:3],
            "duration_min": len(batch) * 3,
            "criticality": "MEDIUM",
            "notes": "Monitor BFD for flapping after each upgrade"
        })

    return stages


def _assess_upgrade_risk(devices: List[Dict], target_version: str) -> Dict[str, Any]:
    """Assess risk of upgrade"""
    return {
        "overall_risk": "MEDIUM",
        "risk_factors": [
            "Production devices will be temporarily impacted during upgrade",
            "BFD sessions may flap during device restart",
            "Rollback may be needed if critical issues detected"
        ],
        "mitigation": [
            "Backup before upgrade",
            "Stage rollout over multiple days",
            "Monitor control plane and data plane metrics during upgrade",
            "Have rollback plan ready"
        ]
    }
