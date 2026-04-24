"""Control plane analysis for Cisco SD-WAN"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ControlPlaneAnalyzer:
    """Analyzes control plane connections and OMP peer health"""

    @staticmethod
    def analyze_control_connections(connections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze control plane connections (device to vManage/vSmart)

        Returns connection health analysis with missing peer detection

        Args:
            connections: List of control connection dictionaries from vManage API

        Returns:
            {
              "vsmart_count": int,
              "vmanage_count": int,
              "expected_vsmart": int,
              "dtls_up": int,
              "tls_up": int,
              "total_up": int,
              "total_down": int,
              "total_connections": int,
              "missing_peers": [...],
              "partially_isolated": [...],
              "recommendations": [...]
            }
        """
        if not connections:
            return {
                "vsmart_count": 0,
                "vmanage_count": 0,
                "dtls_up": 0,
                "tls_up": 0,
                "total_up": 0,
                "total_down": 0,
                "total_connections": 0,
                "missing_peers": [],
                "partially_isolated": [],
                "recommendations": ["No control connections found"]
            }

        vsmart_count = 0
        vmanage_count = 0
        dtls_up = 0
        tls_up = 0
        total_up = 0
        total_down = 0
        missing_peers = []
        device_connections = {}

        for conn in connections:
            state = conn.get("state", "").lower()
            device_id = conn.get("device_id") or conn.get("uuid", "")
            peer_type = conn.get("peer_type", "").lower()
            protocol = conn.get("protocol", "").lower()
            peer_addr = conn.get("peer_ip") or conn.get("peer_addr", "")

            # Track per-device connections
            if device_id not in device_connections:
                device_connections[device_id] = {
                    "total": 0,
                    "up": 0,
                    "down": 0,
                    "connections": []
                }

            device_connections[device_id]["total"] += 1
            device_connections[device_id]["connections"].append(conn)

            # Count by type
            if peer_type == "vsmart":
                vsmart_count += 1
            elif peer_type == "vmanage":
                vmanage_count += 1

            # Count by protocol
            if protocol == "dtls":
                dtls_up += 1 if state == "up" else 0
            elif protocol == "tls":
                tls_up += 1 if state == "up" else 0

            # Count states
            if state == "up":
                total_up += 1
                device_connections[device_id]["up"] += 1
            else:
                total_down += 1
                device_connections[device_id]["down"] += 1
                # Log missing peer
                missing_peers.append({
                    "device": device_id,
                    "peer_type": peer_type,
                    "peer_ip": peer_addr,
                    "protocol": protocol,
                    "state": state
                })

        # Detect completely isolated devices (no UP connections)
        isolated = []
        partially_isolated = []

        for device_id, counts in device_connections.items():
            if counts["up"] == 0:
                isolated.append(device_id)
            elif counts["down"] > 0:
                partially_isolated.append({
                    "device": device_id,
                    "up": counts["up"],
                    "down": counts["down"]
                })

        # Expected vSmart count (usually 3 for redundancy)
        # If we have less than 3, we're missing vSmart peers
        expected_vsmart = 3  # Standard deployment
        missing_vsmart_count = max(0, expected_vsmart - vsmart_count)

        # Generate recommendations
        recommendations = []
        if isolated:
            recommendations.append(f"CRITICAL: {len(isolated)} devices are completely isolated from control plane")

        if partially_isolated:
            recommendations.append(f"WARNING: {len(partially_isolated)} devices have partial control plane connectivity")

        if missing_vsmart_count > 0:
            recommendations.append(f"Missing {missing_vsmart_count} vSmart connections - affects redundancy")

        if total_down > 0 and total_down / (total_up + total_down) > 0.25:
            recommendations.append("More than 25% of control connections are down - investigate control plane connectivity")

        if total_up == 0:
            recommendations.append("CRITICAL: No control plane connectivity detected")

        if not recommendations:
            recommendations.append("Control plane connectivity is healthy")

        # Calculate connection asymmetry (device A has more connections than device B)
        asymmetry_detected = False
        up_counts = [c["up"] for c in device_connections.values()]
        if up_counts and max(up_counts) - min(up_counts) > 1:
            asymmetry_detected = True
            recommendations.append("Asymmetric control plane connections detected - verify vSmart and vManage topology")

        return {
            "vsmart_count": vsmart_count,
            "vmanage_count": vmanage_count,
            "expected_vsmart": expected_vsmart,
            "dtls_up": dtls_up,
            "tls_up": tls_up,
            "total_up": total_up,
            "total_down": total_down,
            "total_connections": len(connections),
            "isolated_devices": isolated,
            "partially_isolated": partially_isolated,
            "missing_peers": missing_peers[:20],  # Top 20
            "asymmetry_detected": asymmetry_detected,
            "recommendations": recommendations
        }

    @staticmethod
    def analyze_omp_peers(peers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze OMP (Overlay Management Protocol) peer status

        Args:
            peers: List of OMP peer dictionaries from vManage API

        Returns:
            {
              "total_peers": int,
              "established_count": int,
              "down_count": int,
              "routes_received_total": int,
              "avg_routes_per_peer": float,
              "issues": [...],
              "recommendations": [...]
            }
        """
        if not peers:
            return {
                "total_peers": 0,
                "established_count": 0,
                "down_count": 0,
                "routes_received_total": 0,
                "avg_routes_per_peer": 0,
                "issues": [],
                "recommendations": ["No OMP peers found"]
            }

        established = 0
        down = 0
        total_routes = 0
        issues = []

        for peer in peers:
            state = peer.get("state", "").lower()
            peer_ip = peer.get("peer_ip") or peer.get("address", "")
            routes_received = int(peer.get("routes_received", 0) or 0)

            total_routes += routes_received

            if state == "established" or state == "up":
                established += 1
            else:
                down += 1
                issues.append({
                    "peer_ip": peer_ip,
                    "state": state,
                    "issue": f"OMP peer down: {peer_ip}",
                    "severity": "high"
                })

            # Low route count from peer
            if routes_received < 10 and state == "established":
                issues.append({
                    "peer_ip": peer_ip,
                    "routes_received": routes_received,
                    "issue": f"Low route count from peer {peer_ip}",
                    "severity": "medium"
                })

        avg_routes = total_routes / established if established > 0 else 0

        # Generate recommendations
        recommendations = []
        if down > 0:
            recommendations.append(f"Troubleshoot {down} down OMP peers - verify vSmart stability")

        if established > 0:
            if avg_routes < 5:
                recommendations.append("Low average route count from OMP peers - verify policy and route distribution")

        if not recommendations:
            recommendations.append("OMP peer status is healthy")

        return {
            "total_peers": len(peers),
            "established_count": established,
            "down_count": down,
            "routes_received_total": total_routes,
            "avg_routes_per_peer": round(avg_routes, 1),
            "issues": issues[:10],
            "recommendations": recommendations
        }

    @staticmethod
    def detect_control_plane_issues(connections: List[Dict[str, Any]],
                                    peers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect control plane issues by correlating connections and OMP peers

        Args:
            connections: Control connection list
            peers: OMP peer list

        Returns:
            {
              "issues": [...],
              "severity": "critical" | "warning" | "info",
              "affected_devices": int
            }
        """
        issues = []
        affected_devices = set()

        # Check for isolated devices
        device_conn = {}
        for conn in connections:
            device = conn.get("device_id")
            if device:
                if device not in device_conn:
                    device_conn[device] = []
                device_conn[device].append(conn)

        for device, conns in device_conn.items():
            up_conns = sum(1 for c in conns if c.get("state", "").lower() == "up")
            if up_conns == 0:
                issues.append({
                    "issue": f"Device {device} is completely isolated from control plane",
                    "severity": "critical",
                    "device": device
                })
                affected_devices.add(device)

        # Check for OMP establishment issues
        for peer in peers:
            if peer.get("state", "").lower() not in ["established", "up"]:
                issues.append({
                    "issue": f"OMP peer {peer.get('peer_ip')} establishment failed",
                    "severity": "high",
                    "peer_ip": peer.get("peer_ip")
                })

        # Determine overall severity
        severity = "info"
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        high_count = sum(1 for i in issues if i["severity"] == "high")

        if critical_count > 0:
            severity = "critical"
        elif high_count > 0:
            severity = "warning"

        return {
            "issues": issues[:15],
            "severity": severity,
            "affected_devices": len(affected_devices),
            "total_issues": len(issues)
        }
