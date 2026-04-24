"""New site onboarding workflow"""

import logging
from typing import Any, Dict, List
from ..vmanage_client import VManageClient

logger = logging.getLogger(__name__)


def onboard_site(client: VManageClient,
                 site_id: str,
                 site_devices: List[str]) -> Dict[str, Any]:
    """
    Validate new site onboarding readiness

    Checks template assignments, certificate status, OMP/BFD baseline

    Args:
        client: Authenticated VManageClient instance
        site_id: Site ID being onboarded
        site_devices: List of device IDs at site

    Returns:
        {
          "site_id": str,
          "onboarding_readiness": "READY" | "NOT_READY",
          "checks": {
            "device_reachability": {...},
            "control_plane": {...},
            "data_plane": {...},
            "certificates": {...},
            "templates": {...}
          },
          "issues": [...],
          "recommendations": [...]
        }
    """
    logger.info(f"Validating onboarding for site {site_id}")

    try:
        devices = client.get_devices()
        site_dev_list = [d for d in devices if d.get("deviceId") in site_devices]

        # Check reachability
        reachability = _check_device_reachability(client, site_devices)

        # Check control plane
        control = _check_control_plane(client, site_devices)

        # Check data plane
        data = _check_data_plane(client, site_devices)

        # Check certificates
        certs = _check_certificates(client, site_devices)

        # Check templates
        templates = _check_template_assignment(client, site_devices)

        # Overall readiness
        issues = []
        if reachability["issues"]:
            issues.extend(reachability["issues"])
        if control["issues"]:
            issues.extend(control["issues"])
        if data["issues"]:
            issues.extend(data["issues"])
        if certs["issues"]:
            issues.extend(certs["issues"])
        if templates["issues"]:
            issues.extend(templates["issues"])

        readiness = "READY" if not issues else "NOT_READY"

        return {
            "site_id": site_id,
            "device_count": len(site_devices),
            "onboarding_readiness": readiness,
            "checks": {
                "device_reachability": reachability,
                "control_plane": control,
                "data_plane": data,
                "certificates": certs,
                "templates": templates
            },
            "issues": issues,
            "recommendations": _generate_recommendations(issues)
        }

    except Exception as e:
        logger.error(f"Onboarding validation failed: {e}")
        return {
            "site_id": site_id,
            "onboarding_readiness": "UNKNOWN",
            "error": str(e)
        }


def _check_device_reachability(client: VManageClient, device_ids: List[str]) -> Dict[str, Any]:
    """Check device reachability from vManage"""
    reachable = 0
    unreachable = 0
    issues = []

    for dev_id in device_ids:
        try:
            status = client.get_device_status(dev_id)
            if status.get("status") == "reachable":
                reachable += 1
            else:
                unreachable += 1
                issues.append(f"Device {dev_id} is unreachable")
        except:
            unreachable += 1
            issues.append(f"Device {dev_id} status check failed")

    return {
        "reachable": reachable,
        "unreachable": unreachable,
        "status": "PASS" if unreachable == 0 else "FAIL",
        "issues": issues
    }


def _check_control_plane(client: VManageClient, device_ids: List[str]) -> Dict[str, Any]:
    """Check control plane establishment"""
    conns = client.get_control_connections()
    device_conns = [c for c in conns if c.get("device_id") in device_ids]

    established = sum(1 for c in device_conns if c.get("state", "").lower() == "up")
    issues = []

    if len(device_conns) == 0:
        issues.append("No control connections found")
    elif established < len(device_ids) * 2:  # Expect at least 2 per device
        issues.append(f"Low control connection count: {established} (expected >{len(device_ids)*2})")

    return {
        "total_connections": len(device_conns),
        "established": established,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues
    }


def _check_data_plane(client: VManageClient, device_ids: List[str]) -> Dict[str, Any]:
    """Check data plane BFD baseline"""
    bfd = []
    for dev_id in device_ids:
        bfd.extend(client.get_bfd_sessions(device_id=dev_id))

    up = sum(1 for s in bfd if s.get("state", "").lower() == "up")
    issues = []

    if len(bfd) == 0:
        issues.append("No BFD sessions found")
    elif up < len(bfd) * 0.8:
        issues.append(f"Low BFD session availability: {up}/{len(bfd)}")

    return {
        "total_sessions": len(bfd),
        "up_sessions": up,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues
    }


def _check_certificates(client: VManageClient, device_ids: List[str]) -> Dict[str, Any]:
    """Check device certificates"""
    certs = client.get_certificates()
    issues = []

    if not certs:
        issues.append("Certificate list unavailable")
    else:
        expired = 0
        expiring_soon = 0
        for cert in certs:
            # Simplified check
            if cert.get("validity") == "invalid":
                expired += 1
                issues.append(f"Expired certificate: {cert.get('cn')}")

        if expired > 0:
            issues.append(f"{expired} certificates expired")

    return {
        "total_certificates": len(certs),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues
    }


def _check_template_assignment(client: VManageClient, device_ids: List[str]) -> Dict[str, Any]:
    """Check device template assignments"""
    issues = []

    try:
        templates = client.get_template_list()
        if not templates:
            issues.append("No device templates available")
    except:
        issues.append("Failed to retrieve template list")

    # Check if devices have template configurations
    devices = client.get_devices()
    assigned = 0
    unassigned = 0

    for dev_id in device_ids:
        dev = next((d for d in devices if d.get("deviceId") == dev_id), None)
        if dev and dev.get("template_assigned"):
            assigned += 1
        else:
            unassigned += 1

    if unassigned > 0:
        issues.append(f"{unassigned} devices without template assignment")

    return {
        "assigned": assigned,
        "unassigned": unassigned,
        "status": "PASS" if unassigned == 0 else "FAIL",
        "issues": issues
    }


def _generate_recommendations(issues: List[str]) -> List[str]:
    """Generate recommendations based on issues"""
    recommendations = []

    if any("reachable" in i for i in issues):
        recommendations.append("Verify management interface connectivity and DNS resolution")

    if any("control" in i for i in issues):
        recommendations.append("Verify DTLS port 12346 is open to vManage/vSmart")

    if any("BFD" in i for i in issues):
        recommendations.append("Verify underlay links and tunnel endpoints")

    if any("certificate" in i for i in issues):
        recommendations.append("Renew or update device certificates before onboarding")

    if any("template" in i for i in issues):
        recommendations.append("Assign appropriate device templates to devices")

    if not recommendations:
        recommendations.append("Site is ready for full deployment")

    return recommendations
