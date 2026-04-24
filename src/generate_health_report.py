from __future__ import annotations
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from report_generator import SDWANReportGenerator


def load_env_file(env_path: Path) -> dict:
    values = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def derive_sastre_env(env_values: dict) -> dict:
    url = env_values.get("VMANAGE_URL", "")
    parsed = urlparse(url)
    host = parsed.hostname or env_values.get("VMANAGE_IP", "")
    port = str(parsed.port or env_values.get("VMANAGE_PORT", "443"))
    user = env_values.get("VMANAGE_USERNAME", env_values.get("VMANAGE_USER", ""))
    pwd = env_values.get("VMANAGE_PASSWORD", "")

    if not host or not user or not pwd:
        raise RuntimeError("Missing required vManage creds in .env (VMANAGE_URL/USERNAME/PASSWORD)")

    out = os.environ.copy()
    out["VMANAGE_IP"] = host
    out["VMANAGE_PORT"] = port
    out["VMANAGE_USER"] = user
    out["VMANAGE_PASSWORD"] = pwd
    return out


def run_sastre(cmd: list[str], env: dict, cwd: Path) -> tuple[bool, str]:
    full = ["sastre"] + cmd
    r = subprocess.run(full, capture_output=True, text=True, cwd=str(cwd), env=env)
    ok = r.returncode == 0
    msg = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
    return ok, msg.strip()


def build_ai_sections(data: dict) -> dict:
    c = data["counts"]
    critical = data["alert_bands"]["Critical"]
    high = data["alert_bands"]["High"]

    overall = "risk-elevated" if (critical or c["unreachable_total"] > 0) else "stable"

    exec_summary = (
        f"Fabric is {overall}: controllers are reachable, but {c['unreachable_total']} device(s) are unreachable and "
        f"alarm pressure is high (Critical={critical}, High={high}). Primary risk is branch resource saturation, not control-plane collapse."
    )

    ccie_summary = (
        f"Sastre state snapshot shows BFD {data['bfd_state'].get('up',0)}/{c['bfd_total']} up, "
        f"control {data['control_state'].get('up',0)}/{c['control_total']} up, and OMP {data['omp_state'].get('up',0)}/{c['omp_total']} up. "
        f"Inventory/state skew should be validated for unreachable nodes with realtime checks. "
        f"Alarm concentration is highest on {', '.join([d for d,_ in data['top_alarm_devices'][:2]]) or 'N/A'} (memory/cpu dominant)."
    )

    findings = (
        f"- Controllers reachable: {c['controllers_total']}/{c['controllers_total']}\n"
        f"- Unreachable devices: {c['unreachable_total']}\n"
        f"- Alarm distribution: Critical {critical}, High {high}, Medium {data['alert_bands']['Medium']}, Low {data['alert_bands']['Low']}\n"
        f"- Top alarm types: {', '.join([f'{t} ({n})' for t,n in data['top_alarm_types'][:3]])}\n"
        f"- Certificates valid: {data['cert_status'].get('valid',0)}/{c['certs_total']}"
    )

    recs = (
        "1) Validate unreachable devices with Sastre realtime checks and controller telemetry correlation.\n"
        "2) Prioritize CPU/memory remediation on top alarming edges; review services, logging, and process utilization.\n"
        "3) Apply phased remediation (canary -> regional -> global) with rollback checkpoints.\n"
        "4) Tune alarm baselines and dampening to reduce noise while preserving critical safety alerts."
    )

    return {
        "executive_summary": exec_summary,
        "ccie_summary": ccie_summary,
        "findings": findings,
        "recommendations": recs,
    }


def main():
    p = argparse.ArgumentParser(description="One-command SD-WAN health report pipeline (Sastre-first)")
    p.add_argument("--project-dir", default=".")
    p.add_argument("--output-dir", default="reports")
    p.add_argument("--alarm-days", default="1")
    p.add_argument("--skip-pull", action="store_true", help="Use existing JSON files without running Sastre")
    args = p.parse_args()

    project_dir = Path(args.project_dir).resolve()
    output_dir = (project_dir / args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_pull:
        env_values = load_env_file(project_dir / ".env")
        sastre_env = derive_sastre_env(env_values)

        steps = [
            (["show", "devices", "--save-json", "devices.json"], "device inventory"),
            (["show", "alarms", "--days", str(args.alarm_days), "--save-json", "alarms.json"], "alarms"),
            (["show", "state", "all", "--save-json", "state.json"], "state"),
            (["list", "certificate", "--save-json", "certificates.json"], "certificates"),
        ]

        for cmd, label in steps:
            ok, msg = run_sastre(cmd, sastre_env, project_dir)
            if not ok:
                raise RuntimeError(f"Sastre pull failed at {label}: {msg}")

    gen = SDWANReportGenerator(project_dir, output_dir)
    data = gen.collect_data()
    ai = build_ai_sections(data)

    ai_file = output_dir / f"ai_sections_autogen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    ai_file.write_text(json.dumps(ai, indent=2), encoding="utf-8")

    report_path = gen.write_report("auto", ai)
    print(str(report_path))


if __name__ == "__main__":
    main()
