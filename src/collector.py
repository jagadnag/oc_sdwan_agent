"""SD-WAN data collection and normalization layer"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .vmanage_client import VManageClient

logger = logging.getLogger(__name__)


class SDWANCollector:
    """
    High-level data collection layer that normalizes and enriches vManage API responses

    Provides domain-specific collection methods (e.g., collect_site_health) that
    combine multiple API calls and normalize results into consistent schemas.
    """

    def __init__(self, client: VManageClient):
        """
        Initialize collector with vManage client

        Args:
            client: Authenticated VManageClient instance
        """
        self.client = client
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes default TTL

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return value
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Store value in cache with timestamp"""
        self.cache[key] = (value, time.time())

    def collect_fabric_overview(self) -> Dict[str, Any]:
        """
        Collect high-level fabric overview

        Returns:
            {
              "devices": [...],
              "reachable_count": int,
              "unreachable_count": int,
              "device_count": int,
              "timestamp": ISO string
            }
        """
        try:
            devices = self.client.get_devices()

            # Enrich with reachability status
            for device in devices:
                device_id = device.get("deviceId") or device.get("uuid")
                if device_id:
                    status = self.client.get_device_status(device_id)
                    device["reachability"] = status.get("status", "unknown")
                else:
                    device["reachability"] = "unknown"

            reachable = sum(1 for d in devices if d.get("reachability") == "reachable")
            unreachable = len(devices) - reachable

            result = {
                "devices": devices,
                "reachable_count": reachable,
                "unreachable_count": unreachable,
                "device_count": len(devices),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self._set_cache("fabric_overview", result)
            return result

        except Exception as e:
            logger.error(f"Failed to collect fabric overview: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_control_plane_health(self) -> Dict[str, Any]:
        """
        Collect control plane health (control connections + OMP peers)

        Returns:
            {
              "control_connections": [...],
              "omp_peers": [...],
              "healthy_connections": int,
              "down_connections": int,
              "timestamp": ISO string
            }
        """
        try:
            connections = self.client.get_control_connections()
            peers = self.client.get_omp_peers()

            # Categorize connections
            healthy = sum(1 for c in connections if c.get("state") == "up")
            down = sum(1 for c in connections if c.get("state") != "up")

            result = {
                "control_connections": connections,
                "omp_peers": peers,
                "healthy_connections": healthy,
                "down_connections": down,
                "total_connections": len(connections),
                "total_peers": len(peers),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect control plane health: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_data_plane_health(self) -> Dict[str, Any]:
        """
        Collect data plane health (BFD sessions + IPsec status)

        Returns:
            {
              "bfd_sessions": [...],
              "up_sessions": int,
              "down_sessions": int,
              "flapping_sessions": int,
              "timestamp": ISO string
            }
        """
        try:
            sessions = self.client.get_bfd_sessions()

            # Analyze BFD health
            up = sum(1 for s in sessions if s.get("state") == "up")
            down = sum(1 for s in sessions if s.get("state") != "up")

            # Detect flapping (state changed multiple times recently)
            flapping = 0
            for session in sessions:
                # Simplified flap detection: if session has recent state changes
                if session.get("state_changes", 0) > 3:
                    flapping += 1

            result = {
                "bfd_sessions": sessions,
                "up_sessions": up,
                "down_sessions": down,
                "total_sessions": len(sessions),
                "flapping_sessions": flapping,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect data plane health: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_site_health(self, site_id: str) -> Dict[str, Any]:
        """
        Collect health data for a specific site (all devices at site)

        Args:
            site_id: Site ID (e.g., "denver-site-1")

        Returns:
            {
              "site_id": str,
              "devices": [...],
              "control_connections": [...],
              "bfd_sessions": [...],
              "alarms": [...],
              "risk_score": float,
              "timestamp": ISO string
            }
        """
        try:
            # Get all devices, filter to site
            all_devices = self.client.get_devices()
            site_devices = [d for d in all_devices if d.get("site-id") == site_id or d.get("siteId") == site_id]

            # Get control connections for site devices
            all_connections = self.client.get_control_connections()
            site_connections = [
                c for c in all_connections
                if any(d.get("deviceId") == c.get("device_id") or d.get("uuid") == c.get("device_id")
                       for d in site_devices)
            ]

            # Get BFD sessions for site devices
            all_bfd = self.client.get_bfd_sessions()
            site_bfd = [
                b for b in all_bfd
                if any(d.get("deviceId") == b.get("device_id") or d.get("uuid") == b.get("device_id")
                       for d in site_devices)
            ]

            # Get alarms for site
            alarms = self.client.get_alarms({"__filter": {"field": "site-id", "value": site_id}})

            result = {
                "site_id": site_id,
                "devices": site_devices,
                "control_connections": site_connections,
                "bfd_sessions": site_bfd,
                "alarms": alarms,
                "device_count": len(site_devices),
                "control_up": sum(1 for c in site_connections if c.get("state") == "up"),
                "bfd_up": sum(1 for b in site_bfd if b.get("state") == "up"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect site health for {site_id}: {e}")
            return {"error": str(e), "site_id": site_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_vpn_health(self, vpn_id: int) -> Dict[str, Any]:
        """
        Collect health data for a specific VPN

        Args:
            vpn_id: VPN ID (0, 512, or service VPN number)

        Returns:
            {
              "vpn_id": int,
              "routes": [...],
              "route_count": int,
              "devices": [...],
              "timestamp": ISO string
            }
        """
        try:
            routes = self.client.get_omp_routes(vpn=vpn_id)

            # Count devices using this VPN
            devices = self.client.get_devices()
            vpn_devices = [d for d in devices]  # All devices could theoretically be on any VPN

            result = {
                "vpn_id": vpn_id,
                "routes": routes,
                "route_count": len(routes),
                "device_count": len(vpn_devices),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect VPN health for VPN {vpn_id}: {e}")
            return {"error": str(e), "vpn_id": vpn_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_alarm_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Collect and summarize alarms

        Args:
            hours: How many hours back to look

        Returns:
            {
              "alarms": [...],
              "critical_count": int,
              "major_count": int,
              "minor_count": int,
              "timestamp": ISO string
            }
        """
        try:
            # vManage alarm query (simplified)
            alarms = self.client.get_alarms()

            critical = sum(1 for a in alarms if a.get("severity") == "critical")
            major = sum(1 for a in alarms if a.get("severity") == "major")
            minor = sum(1 for a in alarms if a.get("severity") == "minor")

            result = {
                "alarms": alarms,
                "total_count": len(alarms),
                "critical_count": critical,
                "major_count": major,
                "minor_count": minor,
                "hours_lookback": hours,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect alarm summary: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_event_timeline(self, hours: int = 24) -> Dict[str, Any]:
        """
        Collect event timeline for causality analysis

        Args:
            hours: How many hours back to look

        Returns:
            {
              "events": [...],
              "event_count": int,
              "timestamp": ISO string
            }
        """
        try:
            # Calculate time window
            now = datetime.utcnow()
            start_time = now - timedelta(hours=hours)

            # Get events (vManage specific query format)
            events = self.client.get_events()

            result = {
                "events": events,
                "event_count": len(events),
                "hours_lookback": hours,
                "start_time": start_time.isoformat() + "Z",
                "end_time": now.isoformat() + "Z",
                "timestamp": now.isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect event timeline: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_certificate_status(self) -> Dict[str, Any]:
        """
        Collect certificate status for all devices

        Returns:
            {
              "certificates": [...],
              "total_count": int,
              "expiring_30days": int,
              "expiring_7days": int,
              "expired": int,
              "timestamp": ISO string
            }
        """
        try:
            certs = self.client.get_certificates()

            now = datetime.utcnow()
            expiring_30 = 0
            expiring_7 = 0
            expired_count = 0

            for cert in certs:
                try:
                    expiry_str = cert.get("expiry_date")
                    if expiry_str:
                        # Parse expiry date (format varies)
                        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                        delta = (expiry - now).days
                        if delta < 0:
                            expired_count += 1
                        elif delta < 7:
                            expiring_7 += 1
                        elif delta < 30:
                            expiring_30 += 1
                except Exception:
                    pass

            result = {
                "certificates": certs,
                "total_count": len(certs),
                "expiring_30days": expiring_30,
                "expiring_7days": expiring_7,
                "expired": expired_count,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect certificate status: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_policy_status(self) -> Dict[str, Any]:
        """
        Collect active centralized policies

        Returns:
            {
              "policies": [...],
              "policy_count": int,
              "timestamp": ISO string
            }
        """
        try:
            policies = self.client.get_policy_list()

            result = {
                "policies": policies,
                "policy_count": len(policies),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect policy status: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_software_compliance(self, target_version: str) -> Dict[str, Any]:
        """
        Collect software version compliance data

        Args:
            target_version: Target software version (e.g., "20.12.4")

        Returns:
            {
              "software": [...],
              "compliant_count": int,
              "non_compliant_count": int,
              "target_version": str,
              "timestamp": ISO string
            }
        """
        try:
            devices = self.client.get_devices()

            compliant = 0
            non_compliant = 0

            for device in devices:
                current_version = device.get("softwareVersion") or device.get("version")
                if current_version == target_version:
                    compliant += 1
                else:
                    non_compliant += 1

            result = {
                "devices": devices,
                "compliant_count": compliant,
                "non_compliant_count": non_compliant,
                "target_version": target_version,
                "device_count": len(devices),
                "compliance_percent": (compliant / len(devices) * 100) if devices else 0,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect software compliance: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_interface_health(self, device_id: str) -> Dict[str, Any]:
        """
        Collect interface health and statistics

        Args:
            device_id: Device ID

        Returns:
            {
              "interfaces": [...],
              "interface_count": int,
              "error_interfaces": int,
              "timestamp": ISO string
            }
        """
        try:
            interfaces = self.client.get_interface_stats(device_id)

            error_interfaces = sum(1 for i in interfaces if i.get("tx_errors", 0) > 0 or i.get("rx_errors", 0) > 0)

            result = {
                "interfaces": interfaces,
                "interface_count": len(interfaces),
                "error_interfaces": error_interfaces,
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect interface health for {device_id}: {e}")
            return {"error": str(e), "device_id": device_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_full_health_snapshot(self) -> Dict[str, Any]:
        """
        Collect comprehensive health snapshot of entire fabric

        Returns composite of all health metrics

        Returns:
            {
              "fabric": {...},
              "control_plane": {...},
              "data_plane": {...},
              "alarms": {...},
              "certificates": {...},
              "policies": {...},
              "timestamp": ISO string
            }
        """
        try:
            logger.info("Collecting full health snapshot...")

            fabric = self.collect_fabric_overview()
            control = self.collect_control_plane_health()
            data = self.collect_data_plane_health()
            alarms = self.collect_alarm_summary()
            certs = self.collect_certificate_status()
            policies = self.collect_policy_status()

            result = {
                "fabric": fabric,
                "control_plane": control,
                "data_plane": data,
                "alarms": alarms,
                "certificates": certs,
                "policies": policies,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self._set_cache("full_health_snapshot", result)
            logger.info("Full health snapshot collected successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to collect full health snapshot: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}

    def collect_device_config(self, device_id: str) -> Dict[str, Any]:
        """
        Collect device running configuration

        Args:
            device_id: Device ID

        Returns:
            {
              "device_id": str,
              "running_config": str,
              "timestamp": ISO string
            }
        """
        try:
            config = self.client.get_running_config(device_id)

            result = {
                "device_id": device_id,
                "running_config": config,
                "config_length": len(config),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return result

        except Exception as e:
            logger.error(f"Failed to collect device config for {device_id}: {e}")
            return {"error": str(e), "device_id": device_id, "timestamp": datetime.utcnow().isoformat() + "Z"}
