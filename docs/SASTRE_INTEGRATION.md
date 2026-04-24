# Sastre CLI Integration Guide

## Overview

**Sastre** is the Cisco DevNet SD-WAN automation tool for bulk configuration management. It specializes in import/export, backup/restore, merge, transform, and policy operations across entire fabric configurations.

Unlike the vManage REST API (which is optimal for querying and monitoring), Sastre excels at **configuration-as-code** workflows:

- Export entire fabric config to version control (Git)
- Bulk attach/detach templates across device groups
- Merge configs from multiple sites/labs
- Transform device configs (find/replace, batch updates)
- Backup/restore entire policy sets

**Reference**: [Sastre on GitHub](https://github.com/CiscoDevNet/sastre)

---

## When to Use Sastre vs REST API

| Use Case | Sastre | REST API |
|----------|--------|---------|
| Export fabric config to file | ✓ | ✗ |
| Backup all templates + policies | ✓ | ✗ (would need script) |
| Query device list | ✗ | ✓ |
| Query alarms | ✗ | ✓ |
| Monitor real-time metrics | ✗ | ✓ |
| Bulk attach template to 50 devices | ✓ | ✓ (REST is more granular) |
| Attach template with preview + approval | ✓ (dryrun) | ✓ (dryrun possible) |
| Restore config from backup | ✓ | ✗ |
| Transform/find-replace config | ✓ | ✗ |
| Verify certificate chain | ✗ | ✓ |
| Check fabric health | ✗ | ✓ |

**Summary**: Use Sastre for bulk configuration operations; use REST API for monitoring and diagnostics.

---

## Installation

### Prerequisites

- Python 3.7+
- pip (Python package manager)
- Access to vManage (same credentials as REST API)

### Install Sastre

```bash
# Option 1: Install from PyPI (recommended for end users)
pip install sastre-pro

# Option 2: Install from source (for development)
git clone https://github.com/CiscoDevNet/sastre.git
cd sastre
pip install -e .

# Verify installation
sastre --version
# Output: Sastre v2.25.x
```

### Configure Credentials

Sastre uses environment variables or a configuration file for vManage credentials.

#### Option 1: Environment Variables (Recommended for CI/CD)

```bash
# Linux/macOS
export VMANAGE_URL="https://192.168.1.10:443"
export VMANAGE_USER="admin"
export VMANAGE_PASSWORD="Cisco123!"
export VMANAGE_VERIFY_SSL="false"  # Lab only; set to "true" in production

# Windows PowerShell
$env:VMANAGE_URL = "https://192.168.1.10:443"
$env:VMANAGE_USER = "admin"
$env:VMANAGE_PASSWORD = "Cisco123!"
$env:VMANAGE_VERIFY_SSL = "false"

# Verify connection
sastre show summary
# Output: Connected to vManage at 192.168.1.10
```

#### Option 2: Config File

Create `~/.sdwan/vmanage_creds.yml`:

```yaml
vmanage_host: 192.168.1.10
vmanage_port: 443
vmanage_user: admin
vmanage_password: Cisco123!
verify_ssl: false
```

```bash
# Sastre will auto-discover this file
sastre show summary
```

#### Option 3: Command-Line Arguments

```bash
sastre -a 192.168.1.10 -u admin -p Cisco123! --verify-ssl false show summary
```

---

## Core Workflows

### 1. Backup Configuration

Export all device templates, feature templates, policies to a file.

```bash
# Full backup of all config
sastre backup production-backup-2025-01-15 \
  --exclude certificates  # Exclude certs (security)

# Output directory structure:
# production-backup-2025-01-15/
#   device_templates/
#   feature_templates/
#   policy_vsmart/
#   policy_localized/
#   policy_definitions/
#   inventory/
#   METADATA

# Restore from backup (dryrun first!)
sastre restore --dryrun production-backup-2025-01-15

# See what changes will be made (preview mode)
# Output: "DRY RUN: 5 templates to attach, 3 policies to update, ..."

# If preview looks good, restore for real
sastre restore production-backup-2025-01-15
```

### 2. List Backups

View all stored backups.

```bash
sastre show backups

# Output:
# Backup ID                          Created         Modified        Devices
# ---------------------------------- --------------- --------------- -------
# production-backup-2025-01-15       2025-01-15      2025-01-15      147
# production-backup-2025-01-08       2025-01-08      2025-01-08      145
# lab-test-2025-01-10                2025-01-10      2025-01-10      45
```

### 3. Export & Import (Config as Code)

Export fabric config to JSON/YAML for version control.

```bash
# Export to JSON (human-readable, version-control friendly)
sastre export production-config-2025-01-15 --format json

# Explore exported structure
tree production-config-2025-01-15/
# device_templates/
#   CSR1000V-Hub.json
#   vedge-CSR1000V.json
#   ...
# feature_templates/
#   AAA-Config.json
#   NTP-Config.json
#   ...
# policy_vsmart/
#   QoS-Traffic-Engineering.json
#   ...

# Version control
cd production-config-2025-01-15
git init
git add -A
git commit -m "Fabric config export as of 2025-01-15"
git remote add origin https://github.com/company/sdwan-config.git
git push -u origin main

# Later, import from Git
git clone https://github.com/company/sdwan-config.git
sastre import --dryrun production-config-2025-01-15
# Dryrun output shows what will attach/detach
```

### 4. Attach/Detach Templates (with Dryrun)

Attach a device template to multiple devices safely.

```bash
# CRITICAL: Always dryrun first!

# Attach template to devices (dryrun)
sastre attach --dryrun \
  --template "CSR1000V-Hub" \
  --devices "10.0.50.1,10.0.51.1,10.0.52.1"

# Dryrun output:
# DRY RUN: Template 'CSR1000V-Hub' would be attached to 3 devices
# - Device 10.0.50.1: IP would change 192.168.1.1 -> 10.0.1.1
# - Device 10.0.51.1: IP would change 192.168.1.2 -> 10.0.2.1
# - Device 10.0.52.1: IP would change 192.168.1.3 -> 10.0.3.1
# Estimated sync time: 3-5 minutes per device

# If happy with dryrun, attach for real
sastre attach \
  --template "CSR1000V-Hub" \
  --devices "10.0.50.1,10.0.51.1,10.0.52.1"

# Monitor attachment progress
watch sastre show device-sync

# Detach template from devices
sastre detach --dryrun \
  --template "CSR1000V-Hub" \
  --devices "10.0.50.1"

# Detach for real (if dryrun looks good)
sastre detach \
  --template "CSR1000V-Hub" \
  --devices "10.0.50.1"
```

### 5. List Devices & Templates

Understand fabric inventory.

```bash
# List all devices
sastre show devices

# Output:
# System IP       Hostname         Model                Reachability
# --------------- --------------- -------------------- ---------------
# 10.0.50.1       vedge-site5     vedge-CSR1000V      reachable
# 10.0.51.1       vedge-site6     vedge-CSR1000V      reachable
# 10.1.1.1        hub-1           vSmartController    reachable
# ...

# List all device templates
sastre show device-templates

# Output:
# Name                               Type         Version  Attached
# ---------------------------------- ------------ -------- --------
# CSR1000V-Hub                       vedge        2        5
# CSR1000V-Spoke                     vedge        1        140
# ...

# List all feature templates
sastre show feature-templates

# Output:
# Name                               Type         Version
# ---------------------------------- ------------ --------
# AAA-Config                         aaa          1
# NTP-Config                         ntp          2
# SNMP-Config                        snmp         1
# ...

# List all policies
sastre show policies

# Output:
# Name                          Type           Version  Sequences
# ----------------------------- -------------- -------- -----------
# QoS-Traffic-Engineering       control        1        3
# AAR-Cloud-Apps                data           2        5
# ...
```

### 6. Verify Certificates

Check certificate status across fabric.

```bash
# Verify all device certificates
sastre verify certificates

# Output:
# Device              Status      Days to Expiry
# ------------------- ----------- ----------------
# 10.0.50.1          valid       127
# 10.0.51.1          valid       128
# 10.1.1.1           valid       243
# ...
# Summary: 145/145 valid, 0 expiring soon, 0 expired

# Export cert chain for external validation
sastre export --cert-chain production-certs
```

### 7. Transform Configuration

Find/replace config across fabric (advanced).

```bash
# Find all occurrences of an IP address
sastre transform \
  --find "192.168.1.0" \
  --scope "all"

# Output:
# Matches found in 10 device configs
# - vedge-site1: VPN 0 interface
# - vedge-site2: VPN 0 interface
# ...

# Replace IP address (dryrun first!)
sastre transform --dryrun \
  --find "192.168.1.0/24" \
  --replace "10.0.0.0/24" \
  --scope "all"

# If dryrun looks good, execute
sastre transform \
  --find "192.168.1.0/24" \
  --replace "10.0.0.0/24" \
  --scope "all"

# Verify changes
git diff  # Compare before/after in version control
```

---

## Integration with SDWAN_AI

SDWAN_AI wraps Sastre workflows in MCP tools, adding safety gates and validation.

### MCP Tool Pattern

```python
# src/tools/configuration_tools.py

import subprocess
import json
import os
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

mcp = None

@mcp.tool
def backup_configuration(
    backup_id: str,
    description: str = "",
    exclude_certificates: bool = True
) -> Dict[str, Any]:
    """Backup entire SD-WAN fabric configuration to file.
    
    Creates a timestamped backup of all templates, policies, and device configs.
    Backup can be used for restore, version control, or analysis.
    
    Args:
        backup_id: Backup directory name (e.g., "prod-backup-2025-01-15")
        description: Optional description for backup
        exclude_certificates: Don't export device certs (security best practice)
    
    Returns:
        {
            "status": "success",
            "backup_id": str,
            "path": str,
            "size_mb": float,
            "config_items": {
                "device_templates": int,
                "feature_templates": int,
                "policies": int,
                "devices": int
            }
        }
    """
    try:
        # Build sastre command
        cmd = ["sastre", "backup", backup_id]
        if exclude_certificates:
            cmd.append("--exclude")
            cmd.append("certificates")
        
        # Execute backup
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            return {
                "status": "error",
                "error": f"Backup failed: {result.stderr}",
                "error_code": "backup_failed"
            }
        
        # Verify backup created
        backup_path = os.path.expanduser(f"~/.sdwan/backups/{backup_id}")
        if not os.path.exists(backup_path):
            return {
                "status": "error",
                "error": f"Backup directory not created: {backup_path}",
                "error_code": "backup_not_found"
            }
        
        # Calculate size
        size_mb = sum(os.path.getsize(os.path.join(dirpath, filename))
                      for dirpath, dirnames, filenames in os.walk(backup_path)
                      for filename in filenames) / (1024 * 1024)
        
        return {
            "status": "success",
            "backup_id": backup_id,
            "path": backup_path,
            "size_mb": round(size_mb, 2),
            "config_items": parse_backup_manifest(backup_path),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Backup timeout (fabric too large)",
            "error_code": "timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "internal_error"
        }

@mcp.tool
def restore_configuration(
    backup_id: str,
    dryrun: bool = True
) -> Dict[str, Any]:
    """Restore fabric configuration from backup (with dryrun validation).
    
    SAFETY: Always run with dryrun=True first to preview changes.
    
    Args:
        backup_id: Backup ID to restore from
        dryrun: If True, only preview what would change (no actual changes)
    
    Returns:
        {
            "status": "success" | "error",
            "mode": "dryrun" | "apply",
            "changes": {
                "templates_attach": [list],
                "templates_detach": [list],
                "policies_attach": [list],
                "policies_detach": [list]
            },
            "affected_devices": int,
            "estimated_sync_time_minutes": int
        }
    """
    try:
        cmd = ["sastre", "restore"]
        if dryrun:
            cmd.append("--dryrun")
        cmd.append(backup_id)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr,
                "error_code": "restore_failed"
            }
        
        # Parse output for change summary
        changes = parse_restore_output(result.stdout)
        
        return {
            "status": "success",
            "mode": "dryrun" if dryrun else "apply",
            "changes": changes,
            "affected_devices": changes.get("device_count", 0),
            "estimated_sync_time_minutes": (changes.get("device_count", 0) * 2) // 60,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "internal_error"
        }

@mcp.tool
def attach_template_dryrun(
    template_name: str,
    device_ips: List[str]
) -> Dict[str, Any]:
    """Preview template attachment (dryrun mode only).
    
    Shows what config changes would occur WITHOUT actually attaching.
    Use this to validate before calling attach_template_apply.
    
    Args:
        template_name: Name of device template (e.g., "CSR1000V-Hub")
        device_ips: List of device system IPs (e.g., ["10.0.50.1", "10.0.51.1"])
    
    Returns:
        {
            "status": "success",
            "dryrun": true,
            "template_name": str,
            "device_count": int,
            "changes": [
                {
                    "device_ip": "10.0.50.1",
                    "hostname": "vedge-site5",
                    "config_changes": ["IP changed 192.168.1.1 -> 10.0.1.1", ...]
                }
            ],
            "estimated_sync_time_minutes": int
        }
    """
    try:
        device_csv = ",".join(device_ips)
        cmd = [
            "sastre", "attach", "--dryrun",
            "--template", template_name,
            "--devices", device_csv
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr,
                "error_code": "dryrun_failed"
            }
        
        changes = parse_attach_dryrun(result.stdout)
        
        return {
            "status": "success",
            "dryrun": True,
            "template_name": template_name,
            "device_count": len(device_ips),
            "changes": changes,
            "estimated_sync_time_minutes": len(device_ips) * 2,
            "next_step": "Review changes above. If approved, call attach_template_apply()"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "internal_error"
        }

@mcp.tool
def attach_template_apply(
    template_name: str,
    device_ips: List[str]
) -> Dict[str, Any]:
    """Apply template attachment to devices (REAL CHANGE).
    
    CAUTION: This actually attaches the template to devices. Always call
    attach_template_dryrun() first to preview changes.
    
    Args:
        template_name: Name of device template
        device_ips: List of device system IPs
    
    Returns:
        {
            "status": "success" | "error",
            "template_name": str,
            "devices_attached": int,
            "devices_failed": int,
            "sync_status": "in_progress" | "completed",
            "estimated_completion_time": "2025-01-15T14:45:00Z"
        }
    """
    try:
        device_csv = ",".join(device_ips)
        cmd = [
            "sastre", "attach",
            "--template", template_name,
            "--devices", device_csv
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr,
                "error_code": "attach_failed"
            }
        
        # Parse attachment status
        attach_result = parse_attach_result(result.stdout)
        
        return {
            "status": "success",
            "template_name": template_name,
            "devices_attached": attach_result.get("success_count", 0),
            "devices_failed": attach_result.get("failure_count", 0),
            "sync_status": "in_progress",
            "estimated_completion_time": (
                (datetime.utcnow() + timedelta(minutes=len(device_ips) * 2))
                .isoformat() + "Z"
            ),
            "next_step": "Monitor device sync status. Run get_device_sync() to check."
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "internal_error"
        }

def parse_backup_manifest(backup_path: str) -> Dict[str, int]:
    """Parse backup manifest to count templates/policies"""
    counts = {
        "device_templates": 0,
        "feature_templates": 0,
        "policies": 0,
        "devices": 0
    }
    # Implementation: parse JSON files in backup_path
    return counts

def parse_restore_output(output: str) -> Dict[str, Any]:
    """Parse sastre restore output for change summary"""
    # Implementation: regex/parse restore output
    return {}

def parse_attach_dryrun(output: str) -> List[Dict[str, Any]]:
    """Parse attachment dryrun output"""
    return []

def parse_attach_result(output: str) -> Dict[str, int]:
    """Parse attachment result (success/failure counts)"""
    return {}
```

### Usage in SDWAN_AI

Architect or operator uses these tools via OpenCode:

```
User: "Attach template 'CSR1000V-Hub' to DC2 sites (5 devices). Show preview first."

Agent Response:
  1. Calls attach_template_dryrun("CSR1000V-Hub", ["10.0.50.1", ...])
  2. Displays dryrun results (config changes, device list)
  3. Waits for user approval

User: "Looks good, apply it."

Agent Response:
  4. Calls attach_template_apply("CSR1000V-Hub", ["10.0.50.1", ...])
  5. Monitors device sync progress
  6. Confirms attachment complete
```

---

## Safety Best Practices

### Rule 1: Always Dryrun First

```bash
# ALWAYS this pattern:
# 1. Dryrun (preview)
sastre attach --dryrun --template X --devices Y

# 2. Review output carefully
# 3. Approve change (human confirmation)
# 4. Execute for real
sastre attach --template X --devices Y
```

### Rule 2: Small Batches

```bash
# BAD: Attach to 100 devices at once (high blast radius)
sastre attach --template X --devices "10.0.1.1,10.0.2.1,...,10.0.100.1"

# GOOD: Attach in batches of 10-20 devices
# Batch 1:
sastre attach --dryrun --template X --devices "10.0.1.1,10.0.2.1,...,10.0.10.1"
# Review and approve
sastre attach --template X --devices "10.0.1.1,10.0.2.1,...,10.0.10.1"
# Monitor sync
# Batch 2:
sastre attach --dryrun --template X --devices "10.0.11.1,10.0.12.1,...,10.0.20.1"
# ... repeat
```

### Rule 3: Version Control

```bash
# Before any bulk change, export current state
sastre export prod-config-pre-change-$(date +%Y-%m-%d)

# Store in Git
git add -A
git commit -m "Baseline before template attachment to DC2 sites"

# Apply change
sastre attach --template X --devices Y

# Export post-change state
sastre export prod-config-post-change-$(date +%Y-%m-%d)

# Git diff to see exact changes
git diff prod-config-pre-change-* prod-config-post-change-*
```

### Rule 4: Backup Before Restore

```bash
# If restoring from backup, first create current backup
sastre backup prod-current-$(date +%Y-%m-%d)

# THEN restore from old backup
sastre restore --dryrun old-backup-id
# Review carefully
sastre restore old-backup-id
```

### Rule 5: Test in Lab

```bash
# Before applying to production:
# 1. Export production config
sastre export prod-config

# 2. Deploy to lab vManage
sastre restore --dryrun prod-config  # On lab
sastre restore prod-config  # On lab

# 3. Test thoroughly in lab
# 4. Only then make change to production
```

---

## Troubleshooting

### Issue: "Authentication Failed"

```bash
# Check credentials
echo $VMANAGE_URL
echo $VMANAGE_USER
# Don't echo password!

# Test connectivity
sastre show summary

# If error: "Invalid credentials"
# Solution: Verify username/password in vManage (case-sensitive)
```

### Issue: "Backup Size Too Large"

```bash
# If backup takes >5 minutes, exclude certificates
sastre backup my-backup --exclude certificates

# Or exclude specific item types
sastre backup my-backup --exclude certificates --exclude events
```

### Issue: "Template Attachment Hangs"

```bash
# If attachment seems stuck, check device sync status
watch sastre show device-sync

# If a device is stuck "syncing" for >10 minutes:
# Option 1: Reboot device (nuclear)
# Option 2: Retry attachment (detach then attach)
sastre detach --template X --devices Y
sastre attach --template X --devices Y
```

### Issue: "Restore Failed - Conflicts"

```bash
# If restore fails due to conflicts, dryrun to see what failed
sastre restore --dryrun backup-id

# Common cause: Device templates not compatible with current version
# Solution: Update device template version first, then restore
```

---

## Advanced: Scripting Sastre for Automation

```bash
#!/bin/bash
# automated-weekly-backup.sh

set -e  # Exit on error

BACKUP_ID="prod-backup-$(date +%Y-%m-%d-%H%M%S)"
LOG_FILE="/var/log/sdwan/sastre-backup-$(date +%Y-%m-%d).log"

echo "Starting weekly backup: $BACKUP_ID" | tee -a $LOG_FILE

# Backup
if sastre backup $BACKUP_ID --exclude certificates >> $LOG_FILE 2>&1; then
    echo "Backup succeeded" | tee -a $LOG_FILE
    
    # Verify backup
    BACKUP_COUNT=$(find ~/.sdwan/backups/$BACKUP_ID -name "*.json" | wc -l)
    echo "Backup contains $BACKUP_COUNT config files" | tee -a $LOG_FILE
    
    # Upload to S3 (offsite backup)
    aws s3 cp ~/.sdwan/backups/$BACKUP_ID s3://company-sdwan-backups/$BACKUP_ID --recursive
    
    # Retention: Keep only last 30 days
    find ~/.sdwan/backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
    
    # Notify ops
    echo "SDWAN backup completed: $BACKUP_ID" | mail -s "Backup success" ops@company.com
else
    echo "Backup failed!" | tee -a $LOG_FILE
    echo "Backup failed: $BACKUP_ID" | mail -s "BACKUP FAILED" ops@company.com
    exit 1
fi
```

---

## References

- [Sastre GitHub Repository](https://github.com/CiscoDevNet/sastre)
- [Sastre Documentation](https://sastre.readthedocs.io/)
- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
- [Cisco DevNet Sandbox (Test Environment)](https://developer.cisco.com/docs/sandbox/)
