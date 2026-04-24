"""FastMCP Server for SDWAN_AI Agent - Cisco SD-WAN AI Sidekick"""

import logging
import sys
from typing import Any, Dict

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Install with: pip install fastmcp")
    sys.exit(1)

from . import tools

# Configure logging to stderr (for MCP communication)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Create FastMCP app
mcp = FastMCP("sdwan-ai-agent")


# ============================================================================
# Inventory Tools
# ============================================================================

@mcp.tool()
def list_devices() -> Dict[str, Any]:
    """
    List all WAN edge devices in fabric

    Returns device list with ID, hostname, model, site ID, reachability, and software version

    Returns:
        Device list with complete inventory details
    """
    return tools.inventory_tools.list_devices()


@mcp.tool()
def list_controllers() -> Dict[str, Any]:
    """
    List all controllers (vManage, vSmart) in fabric

    Returns controller list with status and connectivity

    Returns:
        Controller inventory and status
    """
    return tools.inventory_tools.list_controllers()


@mcp.tool()
def get_device_inventory(device_id: str) -> Dict[str, Any]:
    """
    Get detailed inventory for a specific device

    Args:
        device_id: Device ID or UUID

    Returns:
        Device details including interfaces, certificates, and running configuration
    """
    return tools.inventory_tools.get_device_inventory(device_id)


@mcp.tool()
def get_site_summary(site_id: str) -> Dict[str, Any]:
    """
    Get summary of all devices at a specific site

    Args:
        site_id: Site ID

    Returns:
        Site device summary with counts and types
    """
    return tools.inventory_tools.get_site_summary(site_id)


# ============================================================================
# Control Plane Tools
# ============================================================================

@mcp.tool()
def get_control_connections(device_id: str = None) -> Dict[str, Any]:
    """
    Get control plane connections (device to vManage/vSmart)

    Returns established and down connections with peer addresses and protocol

    Args:
        device_id: Optional device ID to filter

    Returns:
        Control connections with detailed status and analysis
    """
    return tools.control_plane_tools.get_control_connections(device_id)


@mcp.tool()
def check_omp_peers(device_id: str = None) -> Dict[str, Any]:
    """
    Check OMP (Overlay Management Protocol) peer status

    Returns peer establishment state, routes received, and peer health

    Args:
        device_id: Optional device ID to filter

    Returns:
        OMP peers with establishment state and route metrics
    """
    return tools.control_plane_tools.check_omp_peers(device_id)


@mcp.tool()
def get_vsmart_status() -> Dict[str, Any]:
    """
    Get vSmart controller status across fabric

    Returns vSmart controller list with connectivity and OMP establishment state

    Returns:
        vSmart status and redundancy information
    """
    return tools.control_plane_tools.get_vsmart_status()


# ============================================================================
# Data Plane Tools
# ============================================================================

@mcp.tool()
def get_bfd_sessions(device_id: str = None) -> Dict[str, Any]:
    """
    Get BFD session status across fabric or for specific device

    Returns session state (up/down), loss percentage, latency, jitter, color

    Args:
        device_id: Optional device ID to filter

    Returns:
        BFD sessions with performance metrics and analysis
    """
    return tools.data_plane_tools.get_bfd_sessions(device_id)


@mcp.tool()
def get_tunnel_stats(device_id: str = None) -> Dict[str, Any]:
    """
    Get IPsec tunnel statistics (packet counts, throughput)

    Args:
        device_id: Optional device ID to filter

    Returns:
        Tunnel statistics with performance metrics
    """
    return tools.data_plane_tools.get_tunnel_stats(device_id)


@mcp.tool()
def check_tloc_status(device_id: str = None) -> Dict[str, Any]:
    """
    Check TLOC (Transport Locator) status across fabric

    Returns TLOC list with system-ip, color, encapsulation, and status

    Args:
        device_id: Optional device ID to filter

    Returns:
        TLOC status and health information
    """
    return tools.data_plane_tools.check_tloc_status(device_id)


@mcp.tool()
def get_app_route_stats(vpn_id: int = 0) -> Dict[str, Any]:
    """
    Get application-aware routing (AAR) route statistics

    Args:
        vpn_id: VPN ID to filter (default 0 for transport VPN)

    Returns:
        Route statistics and metrics
    """
    return tools.data_plane_tools.get_app_route_stats(vpn_id)


# ============================================================================
# Policy Tools
# ============================================================================

@mcp.tool()
def list_centralized_policies() -> Dict[str, Any]:
    """
    List all centralized policies (control policies, data policies, etc.)

    Returns:
        Policy list with status and device impact
    """
    return tools.policy_tools.list_centralized_policies()


@mcp.tool()
def get_active_policy() -> Dict[str, Any]:
    """
    Get currently active centralized policy

    Returns:
        Active policy details
    """
    return tools.policy_tools.get_active_policy()


@mcp.tool()
def get_aar_policy() -> Dict[str, Any]:
    """
    Get application-aware routing (AAR) policy details

    Returns:
        AAR policy configuration
    """
    return tools.policy_tools.get_aar_policy()


@mcp.tool()
def get_data_policy() -> Dict[str, Any]:
    """
    Get data policy (traffic engineering) details

    Returns:
        Data policy configuration
    """
    return tools.policy_tools.get_data_policy()


# ============================================================================
# Alarm Tools
# ============================================================================

@mcp.tool()
def list_alarms(severity: str = None, limit: int = 50) -> Dict[str, Any]:
    """
    List all alarms with optional severity filtering

    Args:
        severity: Optional severity filter (critical, major, minor)
        limit: Maximum number of alarms to return

    Returns:
        Alarm list with severity breakdown
    """
    return tools.alarm_tools.list_alarms(severity, limit)


@mcp.tool()
def get_alarms_24h(severity: str = None) -> Dict[str, Any]:
    """
    Get alarms from last 24 hours

    Args:
        severity: Optional severity filter

    Returns:
        24-hour alarm history with top issues
    """
    return tools.alarm_tools.get_alarms_24h(severity)


@mcp.tool()
def correlate_alarms(time_window_min: int = 30) -> Dict[str, Any]:
    """
    Correlate alarms to detect patterns and root causes

    Args:
        time_window_min: Time window in minutes for correlation

    Returns:
        Root cause candidates with confidence scores
    """
    return tools.alarm_tools.correlate_alarms(time_window_min)


@mcp.tool()
def get_active_alarms() -> Dict[str, Any]:
    """
    Get currently active alarms (uncleared)

    Returns:
        Active alarm list with severity breakdown
    """
    return tools.alarm_tools.get_active_alarms()


# ============================================================================
# Certificate Tools
# ============================================================================

@mcp.tool()
def list_certificates() -> Dict[str, Any]:
    """
    List all device certificates

    Returns:
        Certificate list with expiry tracking
    """
    return tools.certificate_tools.list_certificates()


@mcp.tool()
def get_expiring_certs(days_warning: int = 30) -> Dict[str, Any]:
    """
    Get certificates expiring within specified days

    Args:
        days_warning: Number of days for expiry warning

    Returns:
        Expiring and expired certificate lists
    """
    return tools.certificate_tools.get_expiring_certs(days_warning)


@mcp.tool()
def check_root_ca() -> Dict[str, Any]:
    """
    Check root CA certificate status

    Returns:
        Root CA status and validity
    """
    return tools.certificate_tools.check_root_ca()


# ============================================================================
# Upgrade Tools
# ============================================================================

@mcp.tool()
def list_software_versions() -> Dict[str, Any]:
    """
    List software versions across all devices

    Returns:
        Software version distribution and device inventory
    """
    return tools.upgrade_tools.list_software_versions()


@mcp.tool()
def get_compliance_status(target_version: str) -> Dict[str, Any]:
    """
    Check software version compliance against target version

    Args:
        target_version: Target software version (e.g., "20.12.4")

    Returns:
        Compliance breakdown and non-compliant device list
    """
    return tools.upgrade_tools.get_compliance_status(target_version)


@mcp.tool()
def plan_software_upgrade(target_version: str, device_filter: str = None) -> Dict[str, Any]:
    """
    Plan software upgrade with staged approach

    Args:
        target_version: Target software version
        device_filter: Optional filter (vedges, controllers)

    Returns:
        Upgrade plan with stages and risk assessment
    """
    return tools.upgrade_tools.plan_software_upgrade(target_version, device_filter)


# ============================================================================
# Sastre Tools
# ============================================================================

@mcp.tool()
def sastre_backup(workdir: str = None, backup_name: str = None) -> Dict[str, Any]:
    """
    Backup device configurations using Sastre

    Args:
        workdir: Working directory for backup (default: ./backup)
        backup_name: Optional backup name

    Returns:
        Backup result with path and status
    """
    return tools.sastre_tools.sastre_backup(workdir, backup_name)


@mcp.tool()
def sastre_inventory() -> Dict[str, Any]:
    """
    Get Sastre inventory information

    Returns:
        Inventory data
    """
    return tools.sastre_tools.sastre_inventory()


@mcp.tool()
def sastre_attach_dryrun(devices: list = None) -> Dict[str, Any]:
    """
    Dry-run template attach operation (no changes)

    Args:
        devices: Optional list of device IDs to filter

    Returns:
        Dry-run result with projected changes
    """
    return tools.sastre_tools.sastre_attach_dryrun(devices)


@mcp.tool()
def sastre_transform(config_dir: str = None) -> Dict[str, Any]:
    """
    Transform configuration data

    Args:
        config_dir: Optional config directory

    Returns:
        Transform operation result
    """
    return tools.sastre_tools.sastre_transform(config_dir)


@mcp.tool()
def sastre_list() -> Dict[str, Any]:
    """
    List devices known to Sastre/controller

    Returns:
        Device list from Sastre
    """
    return tools.sastre_tools.sastre_list()


# ============================================================================
# Workflow Tools
# ============================================================================

@mcp.tool()
def run_morning_health_check() -> Dict[str, Any]:
    """
    Run comprehensive morning health check workflow

    Returns daily health report with fabric status, control/data plane health,
    alarms, certificate expiry warnings, and risk score

    Returns:
        Complete daily health report
    """
    return tools.workflow_tools.run_morning_health_check_tool()




@mcp.tool()
def generate_health_check_report(alarm_days: int = 1, skip_pull: bool = False) -> Dict[str, Any]:
    """
    Generate full SD-WAN health report end-to-end (Sastre-first).

    This tool runs non-interactively and writes a markdown report under ./reports
    with filename: sdwan_controller_<hostname_or_ip>_<datetime>.md

    Args:
        alarm_days: Alarm lookback window in days (default 1)
        skip_pull: Reuse existing Sastre JSON pulls if True

    Returns:
        Report generation result including report path
    """
    return tools.workflow_tools.run_health_report_tool(alarm_days, skip_pull)


@mcp.tool()
def run_incident_triage(site_id_or_device: str, time_window_min: int = 60) -> Dict[str, Any]:
    """
    Triage an incident affecting a site or device

    Performs rapid data collection and correlation to identify root cause

    Args:
        site_id_or_device: Site ID or device ID (e.g., "denver-site-1" or "uuid")
        time_window_min: Time window to analyze (default 60 minutes)

    Returns:
        Triage report with root cause analysis
    """
    return tools.workflow_tools.run_incident_triage_tool(site_id_or_device, time_window_min)


@mcp.tool()
def run_upgrade_plan(target_version: str, device_filter: str = None) -> Dict[str, Any]:
    """
    Plan software upgrade with risk assessment

    Args:
        target_version: Target software version (e.g., "20.12.4")
        device_filter: Optional filter (vedges, controllers)

    Returns:
        Upgrade plan with risk assessment
    """
    return tools.workflow_tools.run_upgrade_plan_tool(target_version, device_filter)


@mcp.tool()
def validate_change_snapshot(change_name: str, snapshot_type: str) -> Dict[str, Any]:
    """
    Take change validation snapshot (pre or post)

    Args:
        change_name: Name of the change (e.g., "Policy Update DR Site")
        snapshot_type: "pre" for pre-change, "post" for post-change

    Returns:
        Snapshot data for comparison
    """
    return tools.workflow_tools.validate_change_snapshot_tool(change_name, snapshot_type)


@mcp.tool()
def compare_change_snapshots(pre_snapshot: Dict, post_snapshot: Dict) -> Dict[str, Any]:
    """
    Compare pre and post change snapshots for validation

    Args:
        pre_snapshot: Pre-change snapshot dictionary
        post_snapshot: Post-change snapshot dictionary

    Returns:
        Validation result with change impact analysis
    """
    return tools.workflow_tools.compare_change_snapshots_tool(pre_snapshot, post_snapshot)


# ============================================================================
# Utility Tools
# ============================================================================

@mcp.tool()
def health_ping() -> Dict[str, Any]:
    """
    Health check endpoint

    Verifies MCP server is operational

    Returns:
        Server health status
    """
    return {
        "success": True,
        "status": "healthy",
        "message": "SDWAN_AI MCP server is operational",
        "version": "1.0.0"
    }


def main():
    """Start the FastMCP server"""
    logger.info("Starting SDWAN_AI MCP server...")
    logger.info("Available tools: 30+ SD-WAN operations including workflows")
    mcp.run(host="localhost", port=4000)


if __name__ == "__main__":
    main()
