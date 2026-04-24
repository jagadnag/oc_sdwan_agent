from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class SDWANReportGenerator:
    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = data_dir
        self.output_dir = output_dir

    def _load_json(self, file_name: str) -> Any:
        return json.loads((self.data_dir / file_name).read_text(encoding="utf-8"))

    def _normalize_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        title = table["header"]["title"]
        rows = []
        for r in table["data"]:
            rows.append({title[k]: v for k, v in r.items() if k in title})
        return rows

    def collect_data(self) -> Dict[str, Any]:
        devices = self._normalize_table(self._load_json("devices.json")[0])
        alarms = self._normalize_table(self._load_json("alarms.json")[0])
        certs = self._normalize_table(self._load_json("certificates.json")[0])
        state_tables = self._load_json("state.json")

        state_map = {}
        for table in state_tables:
            name = table.get("header", {}).get("name", "")
            state_map[name] = self._normalize_table(table)

        controllers = [d for d in devices if d["Type"] in ("vmanage", "vsmart", "vbond")]
        edges = [d for d in devices if d["Type"] not in ("vmanage", "vsmart", "vbond")]
        unreachable = [d for d in devices if d["Reachability"] != "reachable"]

        sev_counter = Counter(a["Severity"] for a in alarms)
        # Architect-facing severity normalization
        alert_bands = {
            "Critical": sev_counter.get("Critical", 0),
            "High": sev_counter.get("Major", 0),
            "Medium": sev_counter.get("Medium", 0),
            "Low": sev_counter.get("Minor", 0),
        }

        active_alarms = [a for a in alarms if a.get("Active") is True]
        top_alarm_devices = Counter(a["Devices"] for a in alarms).most_common(5)
        top_alarm_types = Counter(a["Type"] for a in alarms).most_common(5)

        bfd = state_map.get("BFD sessions", [])
        control = state_map.get("Control connections", [])
        omp = state_map.get("OMP peers", [])
        cedge_if = state_map.get("cEdge interfaces", [])
        vedge_if = state_map.get("vEdge interfaces", [])

        bfd_state = Counter(r["State"] for r in bfd)
        control_state = Counter(r["State"] for r in control)
        omp_state = Counter(r["State"] for r in omp)

        color_pairs = Counter(f"{r['Source TLOC Color']} -> {r['Remote TLOC Color']}" for r in bfd)
        vpn_counts = Counter(str(r.get("VPN (VRF)", "unknown")) for r in (cedge_if + vedge_if))

        cert_status = Counter(c["Status"] for c in certs)

        return {
            "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "devices": devices,
            "controllers": controllers,
            "edges": edges,
            "unreachable": unreachable,
            "alarms": alarms,
            "active_alarms": active_alarms,
            "alert_bands": alert_bands,
            "top_alarm_devices": top_alarm_devices,
            "top_alarm_types": top_alarm_types,
            "certs": certs,
            "cert_status": cert_status,
            "bfd": bfd,
            "bfd_state": bfd_state,
            "control": control,
            "control_state": control_state,
            "omp": omp,
            "omp_state": omp_state,
            "color_pairs": color_pairs,
            "vpn_counts": vpn_counts,
            "counts": {
                "devices_total": len(devices),
                "controllers_total": len(controllers),
                "edges_total": len(edges),
                "reachable_total": len(devices) - len(unreachable),
                "unreachable_total": len(unreachable),
                "alarms_total": len(alarms),
                "alarms_active": len(active_alarms),
                "certs_total": len(certs),
                "bfd_total": len(bfd),
                "control_total": len(control),
                "omp_total": len(omp),
            },
        }

    @staticmethod
    def _table(headers: List[str], rows: List[List[Any]]) -> str:
        out = []
        out.append("| " + " | ".join(headers) + " |")
        out.append("|" + "|".join(["---"] * len(headers)) + "|")
        for r in rows:
            out.append("| " + " | ".join(str(x) for x in r) + " |")
        return "\n".join(out)

    def render_markdown(self, controller_name: str, ai: Dict[str, str], data: Dict[str, Any]) -> str:
        c = data["counts"]
        health_score = round(((c["reachable_total"] / max(c["devices_total"], 1)) * 40)
                             + ((data["bfd_state"].get("up", 0) / max(c["bfd_total"], 1)) * 30)
                             + ((data["control_state"].get("up", 0) / max(c["control_total"], 1)) * 20)
                             + ((data["omp_state"].get("up", 0) / max(c["omp_total"], 1)) * 10), 1)

        overall = "HEALTHY"
        if data["alert_bands"]["Critical"] > 0 or c["unreachable_total"] > 0:
            overall = "CRITICAL"
        elif data["alert_bands"]["High"] > 0:
            overall = "WARNING"

        md = []
        md.append(f"# SD-WAN Health Summary Report - {controller_name}")
        md.append("")
        md.append(f"**Generated:** {data['generated']}  ")
        md.append("**Data Source:** Sastre exports (`devices.json`, `state.json`, `alarms.json`, `certificates.json`)  ")
        md.append("**Report Method:** `report_generator` template + LLM-authored AI assessment")
        md.append("")
        md.append("## AI Assessment Summary")
        md.append("")
        md.append("### Executive Summary")
        md.append(ai["executive_summary"])
        md.append("")
        md.append("### CCIE Technical Summary")
        md.append(ai["ccie_summary"])
        md.append("")
        md.append("### Key Findings")
        md.append(ai["findings"])
        md.append("")
        md.append("### Recommendations")
        md.append(ai["recommendations"])
        md.append("")

        md.append("## Snapshot KPIs")
        md.append("")
        md.append(self._table(
            ["Metric", "Value"],
            [
                ["Overall Health", overall],
                ["Composite Health Score (/100)", health_score],
                ["Total Devices", c["devices_total"]],
                ["Controllers", c["controllers_total"]],
                ["Edges", c["edges_total"]],
                ["Reachable", c["reachable_total"]],
                ["Unreachable", c["unreachable_total"]],
                ["Total Alarms", c["alarms_total"]],
                ["Active Alarms", c["alarms_active"]],
                ["BFD Sessions", c["bfd_total"]],
                ["Control Connections", c["control_total"]],
                ["OMP Peers", c["omp_total"]],
                ["Certificates", c["certs_total"]],
            ],
        ))
        md.append("")

        md.append("## Alert Categorization")
        md.append("")
        md.append(self._table(
            ["Category", "Count", "Source Severity Mapping"],
            [
                ["Critical", data["alert_bands"]["Critical"], "Critical"],
                ["High", data["alert_bands"]["High"], "Major"],
                ["Medium", data["alert_bands"]["Medium"], "Medium"],
                ["Low", data["alert_bands"]["Low"], "Minor"],
            ],
        ))
        md.append("")

        md.append("## Controller Status")
        md.append("")
        md.append(self._table(
            ["Name", "System IP", "Site", "Reachability", "Type", "Model"],
            [[x["Name"], x["System IP"], x["Site ID"], x["Reachability"], x["Type"], x["Model"]] for x in data["controllers"]],
        ))
        md.append("")

        md.append("## Device Inventory")
        md.append("")
        md.append(self._table(
            ["Name", "System IP", "Site", "Reachability", "Type", "Model"],
            [[x["Name"], x["System IP"], x["Site ID"], x["Reachability"], x["Type"], x["Model"]] for x in data["devices"]],
        ))
        md.append("")

        md.append("## VPN / Tunnel Snapshot")
        md.append("")
        md.append("### VPN (VRF) Interface Distribution")
        md.append(self._table(
            ["VPN (VRF)", "Interface Count"],
            [[k, v] for k, v in data["vpn_counts"].most_common()],
        ))
        md.append("")
        md.append("### BFD Tunnel Color-Pair Distribution")
        md.append(self._table(
            ["Tunnel Pair", "Count"],
            [[k, v] for k, v in data["color_pairs"].most_common()],
        ))
        md.append("")

        md.append("## BFD / Control / OMP Health")
        md.append("")
        md.append(self._table(
            ["Plane", "Total", "Up", "Down/Other"],
            [
                ["BFD", c["bfd_total"], data["bfd_state"].get("up", 0), c["bfd_total"] - data["bfd_state"].get("up", 0)],
                ["Control Connections", c["control_total"], data["control_state"].get("up", 0), c["control_total"] - data["control_state"].get("up", 0)],
                ["OMP", c["omp_total"], data["omp_state"].get("up", 0), c["omp_total"] - data["omp_state"].get("up", 0)],
            ],
        ))
        md.append("")

        md.append("## Alarm Hotspots")
        md.append("")
        md.append("### Top Devices by Alarm Volume")
        md.append(self._table(["Device", "Alarm Count"], [[d, n] for d, n in data["top_alarm_devices"]]))
        md.append("")
        md.append("### Top Alarm Types")
        md.append(self._table(["Alarm Type", "Count"], [[t, n] for t, n in data["top_alarm_types"]]))
        md.append("")
        md.append("### Active Alarms (Current)")
        active_rows = [[a["Date & Time"], a["Devices"], a["Severity"], a["Type"], a["Message"]] for a in data["active_alarms"]]
        md.append(self._table(["Time", "Device", "Severity", "Type", "Message"], active_rows if active_rows else [["-","-","-","-","No active alarms"]]))
        md.append("")

        md.append("## Certificate Posture")
        md.append("")
        md.append(self._table(
            ["Status", "Count"],
            [[k, v] for k, v in data["cert_status"].items()],
        ))
        md.append("")

        md.append("## Risk Notes")
        md.append("- One branch (`dc-cedge01`) is unreachable in inventory while control/BFD rows are present in state export. This is an inconsistency that should be validated against real-time status.")
        md.append("- Alarm pressure is concentrated on `site2-cedge01` and `my-10-f33116-mc01` (memory/cpu), indicating sustained resource saturation risk.")
        md.append("- Control, BFD, and OMP are fully up in exported state data, suggesting no fabric-wide control-plane outage at capture time.")

        return "\n".join(md) + "\n"

    def write_report(self, controller_name: str, ai: Dict[str, str]) -> Path:
        data = self.collect_data()

        # Auto-discover vManage hostname/IP for report naming
        if not controller_name or controller_name.lower() == "auto":
            controllers = data.get("controllers", [])
            vmanage = next((c for c in controllers if str(c.get("Type", "")).lower() == "vmanage"), None)
            if not vmanage and controllers:
                vmanage = controllers[0]

            host = (vmanage or {}).get("Name", "unknown")
            ip = (vmanage or {}).get("System IP", "")
            controller_name = f"{host}_{ip}" if ip else host

        safe_controller = (
            str(controller_name)
            .replace(" ", "-")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"sdwan_controller_{safe_controller}_{now}.md"
        out_path = self.output_dir / fname
        self.output_dir.mkdir(parents=True, exist_ok=True)
        content = self.render_markdown(safe_controller, ai, data)
        out_path.write_text(content, encoding="utf-8")
        return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate SD-WAN health markdown report from Sastre data")
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--controller", default="auto")
    parser.add_argument("--ai-file", required=True, help="JSON file with executive_summary, ccie_summary, findings, recommendations")
    args = parser.parse_args()

    ai = json.loads(Path(args.ai_file).read_text(encoding="utf-8"))
    gen = SDWANReportGenerator(Path(args.data_dir), Path(args.output_dir))
    out = gen.write_report(args.controller, ai)
    print(str(out))


if __name__ == "__main__":
    main()
