# Extending SDWAN_AI: Adding Skills, Tools, Agents, and MCP Servers

This guide shows how to extend SDWAN_AI with new capabilities.

---

## Architecture Review

Before extending, understand the four extension points:

```
OpenCode Framework
├─→ Agents (.opencode/agents/) - Different AI personas
├─→ Skills (.opencode/skills/) - Domain-specific workflows
├─→ MCP Servers (src/*_mcp_server.py) - Tool execution engines
└─→ Tools (src/tools/) - Individual MCP-registered functions
```

### Relationship

```
Agent (architect.md)
  ├─→ Uses skill (daily-health-check/SKILL.md)
  │     └─→ Calls MCP tools
  │         └─→ Invokes specific tools (get_devices, get_alarms)
  │
  └─→ Uses skill (alarm-correlation/SKILL.md)
        └─→ Calls MCP tools
            └─→ Invokes specific tools (get_alarms, analyze_alarms)
```

---

## 1. Add a New Skill

A **skill** is a domain-specific workflow that uses MCP tools to accomplish a task.

### Example: Create "Bandwidth-Optimization" Skill

**What it does**: Identifies underutilized circuits and recommends consolidation.

### Step 1: Create Skill Directory

```bash
mkdir -p .opencode/skills/bandwidth-optimization
```

### Step 2: Create SKILL.md (Frontmatter + Instructions)

```markdown
# File: .opencode/skills/bandwidth-optimization/SKILL.md

---
id: bandwidth-optimization
name: Bandwidth Optimization
description: Analyze circuit utilization and recommend bandwidth consolidation strategies
author: Architecture Team
created: 2025-01-15
version: 1.0
tags:
  - capacity-planning
  - cost-optimization
  - network-design
difficulty: intermediate
estimated_duration: 15 minutes
required_permissions:
  - read:devices
  - read:statistics
  - read:policies
---

## Bandwidth Optimization Workflow

You are assisting a network architect in identifying bandwidth cost reduction opportunities.

### Objective

Analyze circuit utilization patterns across the fabric and recommend consolidation strategies.

### Instructions

1. **Collect Utilization Data**
   - Get all sites and their primary/backup circuit information
   - Fetch 30-day bandwidth statistics for each site
   - Identify 95th percentile usage (SLA baseline)

2. **Analyze Utilization**
   - Calculate utilization ratio: 95th% / SLA
   - Identify underutilized circuits (utilization < 30%)
   - Identify overutilized circuits (utilization > 80%)
   - Group by ISP carrier (for bulk negotiation)

3. **Recommend Consolidation**
   - Low-utilization sites (< 30%): Can reduce SLA by 50%
   - High-utilization sites (> 80%): Recommend upgrade before consolidation
   - Multi-carrier sites: Consider single-carrier with backup MPLS

4. **Risk Assessment**
   - Any site relying on single carrier? (disaster risk)
   - Backup circuit utilization? (should be <50% for failover capacity)
   - SLA compliance status? (all circuits meeting SLA?)

5. **Estimate Savings**
   - Calculate monthly savings: (Current SLA - Recommended SLA) * Circuit Cost
   - Sum across all consolidation opportunities
   - Payback period: (Change Management Cost) / Monthly Savings

6. **Document Recommendations**
   - Tier 1: Safe consolidations (low risk, immediate savings)
   - Tier 2: Conditional consolidations (requires monitoring)
   - Tier 3: Future consolidations (dependent on other projects)

### Output Format

Provide findings in structured format:

```
BANDWIDTH OPTIMIZATION ANALYSIS
================================

Executive Summary
- Total Monthly Savings Opportunity: $X,XXX
- Consolidation Candidates: N sites
- Risk Level: [LOW | MEDIUM | HIGH]

Current State
- Total Sites: 147
- Total Monthly Cost: $X,XXX
- 95th% Avg Utilization: Y%

Consolidation Opportunities

Tier 1 (Safe): Immediate Implementation
[ Site list with current SLA, recommended SLA, monthly savings ]

Tier 2 (Conditional): Monitor for 30 days
[ Site list with conditions ]

Tier 3 (Future): Pending other projects
[ Site list ]

Implementation Plan
1. [Action 1] - Timeline
2. [Action 2] - Timeline
3. ...

Risk Mitigation
- [Risk 1] - Mitigation strategy
- [Risk 2] - Mitigation strategy
```

### MCP Tools Used

- `get_devices(device_type="vedges")` - List all edge sites
- `get_interface_stats(system_ip, time_window_days=30)` - Bandwidth utilization
- `get_approute_stats(time_window)` - Application traffic patterns
- `analyze_circuit_health(site_id)` - ISP reliability data
- `get_control_connections(system_ip)` - Control plane overhead

### Related Skills

- capacity-planning: For detailed growth projections
- onboarding: When adding new sites

### Assumptions

- Cisco SD-WAN with consistent vManage deployment
- At least 30 days of historical data available
- ISP cost data provided externally (not in vManage)
```

### Step 3: Update opencode.json

Add skill to agent configuration:

```json
{
  "agent": {
    "sdwan-architect": {
      "mode": "primary",
      "skills": [
        "daily-health-check",
        "capacity-planning",
        "bandwidth-optimization",  // NEW
        "..."
      ]
    }
  }
}
```

### Step 4: Test Skill

```bash
opencode

# In agent:
> sdwan-architect: Analyze bandwidth optimization opportunities

# Agent should:
# 1. Recognize bandwidth-optimization skill
# 2. Invoke MCP tools
# 3. Execute analysis
# 4. Return formatted recommendations
```

---

## 2. Add a New MCP Tool

A **tool** is an individual function registered with the MCP server, callable by the LLM.

### Example: Create "analyze_traffic_path" Tool

**What it does**: Traces traffic path from source to destination through SD-WAN fabric.

### Step 1: Create Tool Function

```python
# File: src/tools/routing_tools.py

import logging
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = None

def set_mcp_instance(mcp_instance):
    global mcp
    mcp = mcp_instance

@mcp.tool
def analyze_traffic_path(
    source_ip: str,
    dest_ip: str,
    protocol: str = "tcp",
    dest_port: Optional[int] = None
) -> Dict[str, Any]:
    """Analyze and trace traffic path through SD-WAN fabric.
    
    Determines which tunnel and policy controls traffic from source to destination.
    Useful for troubleshooting application routing, AAR policy validation, and path analysis.
    
    Args:
        source_ip: Source IP address (e.g., 192.168.1.100)
        dest_ip: Destination IP address (e.g., 8.8.8.8)
        protocol: Protocol (tcp, udp, icmp)
        dest_port: Destination port (optional, for TCP/UDP)
    
    Returns:
        {
            "status": "success",
            "source_ip": str,
            "dest_ip": str,
            "path": {
                "ingress_device": str,
                "ingress_vpn": int,
                "matching_policy": str,
                "action": "primary-path" | "backup-path" | "best-path",
                "primary_tunnel": {
                    "remote_system_ip": str,
                    "color": str,
                    "state": "up" | "down",
                    "latency_ms": float,
                    "loss_percent": float
                },
                "backup_tunnel": {...} or None,
                "tunnel_status": "primary-active" | "primary-backup-active" | "backup-active-failover",
                "policy_applied": {
                    "policy_name": str,
                    "rule_name": str,
                    "match_criteria": [...],
                    "action": str
                } or None
            },
            "recommendations": [...]
        }
    """
    try:
        # Determine ingress device (where traffic originates)
        # This requires checking ARP/routing to find local attachment point
        ingress_device = determine_source_device(source_ip)
        if not ingress_device:
            return {
                "status": "error",
                "error": f"Cannot determine source device for {source_ip}",
                "error_code": "source_device_not_found"
            }
        
        # Get source device details
        device_status = mcp.vmanage_client.get_device_status(ingress_device)
        source_vpn = determine_vpn(source_ip, ingress_device)  # VPN 0, 10, etc.
        
        # Check routing table on source device
        # (Would require traceroute or BGP table access)
        routing_entry = get_routing_entry(ingress_device, dest_ip)
        
        if not routing_entry:
            return {
                "status": "error",
                "error": f"No route to {dest_ip}",
                "error_code": "no_route"
            }
        
        # Determine which tunnel matches destination
        # Check localized policy on source device
        localized_policy = mcp.vmanage_client.get_localized_policy(ingress_device)
        
        # Check centralized policy on control plane
        matching_policies = find_matching_policy(
            source_vpn,
            source_ip,
            dest_ip,
            protocol,
            dest_port
        )
        
        # Get tunnel state for matching color(s)
        bfd_sessions = mcp.vmanage_client.get_bfd_sessions(ingress_device)
        
        # Determine active tunnel
        primary_tunnel = select_primary_tunnel(bfd_sessions, routing_entry)
        backup_tunnel = select_backup_tunnel(bfd_sessions, routing_entry)
        
        # Determine which is actually active
        tunnel_status = "primary-active"
        if primary_tunnel.get("state") == "down" and backup_tunnel:
            tunnel_status = "backup-active-failover"
        elif not primary_tunnel and backup_tunnel:
            tunnel_status = "backup-active-failover"
        
        # Recommendations
        recommendations = []
        if primary_tunnel.get("state") == "down":
            recommendations.append("Primary tunnel down; traffic using backup. Investigate primary tunnel.")
        if primary_tunnel.get("loss_percent", 0) > 1.0:
            recommendations.append(f"Primary tunnel has {primary_tunnel['loss_percent']}% loss. Monitor or failover to backup.")
        if not matching_policies:
            recommendations.append("No explicit policy matched; using default TLOC preference. Consider adding AAR policy.")
        
        return {
            "status": "success",
            "source_ip": source_ip,
            "dest_ip": dest_ip,
            "path": {
                "ingress_device": ingress_device,
                "ingress_vpn": source_vpn,
                "matching_policy": matching_policies[0].get("name") if matching_policies else None,
                "action": matching_policies[0].get("action", "best-path") if matching_policies else "best-path",
                "primary_tunnel": {
                    "remote_system_ip": primary_tunnel.get("peer-system-ip"),
                    "color": primary_tunnel.get("color"),
                    "state": primary_tunnel.get("state"),
                    "latency_ms": primary_tunnel.get("latency"),
                    "loss_percent": primary_tunnel.get("loss-percent", 0),
                    "jitter_ms": primary_tunnel.get("jitter", 0)
                },
                "backup_tunnel": {
                    "remote_system_ip": backup_tunnel.get("peer-system-ip"),
                    "color": backup_tunnel.get("color"),
                    "state": backup_tunnel.get("state"),
                    "latency_ms": backup_tunnel.get("latency"),
                    "loss_percent": backup_tunnel.get("loss-percent", 0)
                } if backup_tunnel else None,
                "tunnel_status": tunnel_status,
                "policy_applied": {
                    "policy_name": matching_policies[0].get("name"),
                    "rule_name": matching_policies[0].get("rule"),
                    "match_criteria": [
                        f"Source: {source_ip}",
                        f"Destination: {dest_ip}",
                        f"Protocol: {protocol}",
                        f"Port: {dest_port}" if dest_port else None
                    ],
                    "action": matching_policies[0].get("action")
                } if matching_policies else None
            },
            "recommendations": recommendations,
            "investigation_time_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
    
    except Exception as e:
        logger.error(f"Error analyzing traffic path: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_code": "analysis_failed"
        }

# Helper functions
def determine_source_device(source_ip: str) -> Optional[str]:
    """Determine which device source IP belongs to (by ARP/routing lookup)"""
    # Implementation: Query vManage for device with this IP
    pass

def determine_vpn(source_ip: str, device: str) -> int:
    """Determine which VPN (0, 10, etc.) source IP belongs to"""
    pass

def get_routing_entry(device: str, dest_ip: str) -> Optional[Dict]:
    """Get routing table entry for destination"""
    pass

def find_matching_policy(vpn: int, src: str, dst: str, proto: str, port: Optional[int]) -> List[Dict]:
    """Find policies matching traffic flow"""
    pass

def select_primary_tunnel(sessions: List[Dict], routing: Dict) -> Dict:
    """Select primary tunnel based on TLOC preference"""
    pass

def select_backup_tunnel(sessions: List[Dict], routing: Dict) -> Optional[Dict]:
    """Select backup tunnel if available"""
    pass
```

### Step 2: Register Tool in MCP Server

```python
# File: src/mcp_server.py

from mcp.server.fastmcp import FastMCP
from .tools import routing_tools

mcp = FastMCP("sdwan-tools", "1.0.0")

# Initialize vManage client
vmanage_client = VManageClient(...)

# Register tool module
routing_tools.set_mcp_instance(mcp)
routing_tools.mcp = mcp  # Inject MCP reference

if __name__ == "__main__":
    mcp.run()
```

### Step 3: Test Tool

```bash
# Start MCP server
python src/mcp_server.py

# In another terminal, test with OpenCode
opencode

# Prompt:
> sdwan-architect: Trace traffic path from 192.168.1.100 to 8.8.8.8 (TCP port 443)

# Agent should:
# 1. Call analyze_traffic_path(...)
# 2. Display path analysis with recommendations
```

---

## 3. Add a New Agent Persona

An **agent** is a distinct AI persona with different goals, permissions, and instructions.

### Example: Create "sdwan-ciso" Persona

**Who**: Chief Information Security Officer (security-focused perspective)

### Step 1: Create Agent Prompt

```markdown
# File: prompts/sdwan-ciso.md

# SDWAN_AI CISO Persona & Security Operating Manual

## Who You Are

You are **SDWAN_AI CISO**, the security-focused sidekick for an enterprise Chief Information Security Officer.

You have:
- **20+ years** experience in enterprise security
- **CISSP**, **CISM** certifications
- **Authority** to recommend security policies, audit trails, compliance measures
- **Zero-trust mindset** - verify everything, trust nothing

Your role is to help the CISO:
1. Ensure SD-WAN security posture against evolving threats
2. Validate compliance with corporate security policies
3. Audit user access and configuration changes
4. Recommend zero-trust architecture improvements
5. Prepare incident response playbooks

## Your Mission

### Threat Model Thinking

You think in terms of:
- **Confidentiality**: Is traffic encrypted? Are encryption keys managed securely?
- **Integrity**: Can unauthorized users modify configs? Are changes audited?
- **Availability**: Can attackers DoS the fabric? Is redundancy in place?
- **Accountability**: Are all user actions logged? Can we audit historical changes?

### Key Responsibilities

1. **Certificate & Trust Management**
   - Audit certificate chain (root CA → device certs)
   - Identify expiring certificates (proactive renewal)
   - Validate certificate revocation status
   - Recommend key rotation strategy

2. **Authentication & Access Control**
   - Verify vManage RBAC (least privilege)
   - Audit admin user accounts (MFA required?)
   - Check AAA configuration (RADIUS/TACACS+ secure?)
   - Validate session timeouts

3. **Encryption & Data Protection**
   - Verify all tunnels use strong IPsec encryption (AES-256)
   - Audit DPD (Dead Peer Detection) settings
   - Check Perfect Forward Secrecy (PFS) enabled
   - Validate no plaintext control traffic

4. **Configuration & Change Management**
   - Audit template/policy changes (who changed what, when)
   - Verify approval workflow (no unauthorized changes)
   - Check policy backup/restore audit trail
   - Validate configuration versioning in Git

5. **Threat Intelligence Integration**
   - Monitor for known vulnerabilities in device OS versions
   - Check for malware/botnet C&C communications (via App Aware Routing)
   - Validate URL filtering policies (block malicious categories)
   - Recommend security package updates

## Permission Model

- vManage API: read-only (query configs, audit logs, certificate status)
- Bash: ask-before-run (never auto-execute security commands)
- Edit: deny (no direct file editing; changes via vManage API only)
- WebFetch: deny

## Typical Workflows

### 1. Security Posture Audit (Monthly)
- Certificate expiry sweep
- RBAC review (identify over-privileged users)
- Encryption cipher audit
- Access log review
- Vulnerability scan (devices running patched OS versions?)

### 2. Incident Investigation
- Audit config changes around incident time
- Check authentication logs (unauthorized admin logins?)
- Validate no policy bypass (AAR policy misconfiguration?)
- Check AppRoute for C&C callbacks

### 3. Compliance Validation (Quarterly)
- SOC2 readiness (are logs exported to SIEM?)
- PCI-DSS compliance (encryption, access control)
- HIPAA audit readiness (data encryption, access control)
- Zero-trust readiness (segmentation, encryption, authentication)

## Sample Prompt

User: "Is our SD-WAN fabric secure?"

You provide:
1. **Certificate Status**: All certs valid? Any expiring soon?
2. **Access Control**: Who has admin? Are non-admins locked down?
3. **Encryption**: All tunnels encrypted? Cipher strength?
4. **Config Integrity**: Are changes audited? Backup tested?
5. **Threat Prevention**: URL filtering enabled? IPS/IDS rules current?
6. **Incident Readiness**: Can we detect/respond to attacks? Are logs available?

Then provide findings + risk rating (LOW/MEDIUM/HIGH) + remediation roadmap.
```

### Step 2: Update opencode.json

```json
{
  "agent": {
    "sdwan-ciso": {
      "mode": "all",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/sdwan-ciso.md}",
      "permission": {
        "edit": "deny",
        "bash": "ask",
        "webfetch": "deny"
      }
    }
  }
}
```

### Step 3: Test Agent

```bash
opencode

# Switch to new agent
> switch sdwan-ciso

# Prompt:
> sdwan-ciso: Run security posture audit

# Agent should use security-focused perspective
```

---

## 4. Add a New MCP Server (Advanced)

A **MCP server** is a separate process that provides a set of tools. This enables multi-provider architectures.

### Example: Add ThousandEyes Integration

**Why**: ThousandEyes provides ISP circuit health monitoring; SD-WAN BFD + TE correlation = root cause diagnosis.

### Step 1: Create MCP Server

```python
# File: src/te_mcp_server.py

from mcp.server.fastmcp import FastMCP
import requests
import os
import logging

logger = logging.getLogger(__name__)

mcp = FastMCP("thousandeyes-tools", "1.0.0")

TE_API_BASE = "https://api.thousandeyes.com/v7"
TE_API_TOKEN = os.environ.get("TE_API_TOKEN")

@mcp.tool
def get_network_tests(test_type: str = None) -> dict:
    """List all ThousandEyes network tests.
    
    Args:
        test_type: Filter by test type (http-server, dns, bgp, etc.)
    
    Returns:
        {"tests": [...], "count": N}
    """
    try:
        headers = {"Authorization": f"Bearer {TE_API_TOKEN}"}
        response = requests.get(f"{TE_API_BASE}/tests", headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        tests = data.get("test", [])
        
        if test_type:
            tests = [t for t in tests if t.get("type") == test_type]
        
        return {
            "status": "success",
            "tests": tests,
            "count": len(tests)
        }
    except Exception as e:
        logger.error(f"Failed to get TE tests: {e}")
        return {"status": "error", "error": str(e)}

@mcp.tool
def get_test_metrics(test_id: str, metric: str = "latency", duration_hours: int = 24) -> dict:
    """Get metrics for a specific test.
    
    Args:
        test_id: Test ID (from get_network_tests)
        metric: Metric type (latency, loss, jitter, availability)
        duration_hours: Historical window (1-720 hours)
    
    Returns:
        {"metric": metric, "data": [...], "stats": {...}}
    """
    try:
        headers = {"Authorization": f"Bearer {TE_API_TOKEN}"}
        from_time = int(time.time()) - (duration_hours * 3600)
        
        url = f"{TE_API_BASE}/tests/{test_id}/results"
        params = {
            "metrics": metric,
            "from": from_time
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse results
        results = data.get("results", [])
        
        # Calculate stats
        values = [r.get(metric, 0) for r in results if metric in r]
        stats = {
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "avg": sum(values) / len(values) if values else 0,
            "p95": percentile(values, 95) if values else 0
        }
        
        return {
            "status": "success",
            "test_id": test_id,
            "metric": metric,
            "duration_hours": duration_hours,
            "data_points": len(results),
            "stats": stats,
            "data": results[-20:]  # Last 20 data points
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool
def correlate_bfd_with_circuit(bfd_session: dict, te_test_id: str) -> dict:
    """Correlate SD-WAN BFD session with ThousandEyes circuit health.
    
    Args:
        bfd_session: BFD session dict from get_bfd_sessions
        te_test_id: TE test ID monitoring this circuit
    
    Returns:
        Root cause analysis combining both data sources
    """
    try:
        # Get TE metrics
        te_metrics = get_test_metrics(te_test_id, "latency")
        if te_metrics.get("status") != "success":
            return te_metrics
        
        # Get loss metrics
        te_loss = get_test_metrics(te_test_id, "loss")
        
        # Analyze correlation
        bfd_flaps = bfd_session.get("flap-count", 0)
        bfd_loss = bfd_session.get("loss-percent", 0)
        circuit_latency = te_metrics.get("stats", {}).get("avg", 0)
        circuit_loss = te_loss.get("stats", {}).get("avg", 0)
        
        # Root cause logic
        root_causes = []
        
        if circuit_latency > 100 and bfd_flaps > 5:
            root_causes.append({
                "cause": "Circuit latency spike",
                "confidence": 0.95,
                "evidence": [
                    f"TE latency: {circuit_latency}ms (elevated)",
                    f"BFD flaps: {bfd_flaps} (high)"
                ]
            })
        
        if circuit_loss > 1.0 and bfd_loss > 1.0:
            root_causes.append({
                "cause": "ISP packet loss",
                "confidence": 0.90,
                "evidence": [
                    f"TE loss: {circuit_loss}%",
                    f"BFD loss: {bfd_loss}%"
                ]
            })
        
        return {
            "status": "success",
            "root_causes": root_causes,
            "recommendation": "Contact ISP to investigate circuit health" if root_causes else "No circuit issues detected"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def percentile(data, p):
    """Calculate percentile"""
    sorted_data = sorted(data)
    index = int(len(sorted_data) * (p / 100))
    return sorted_data[index] if index < len(sorted_data) else sorted_data[-1]

if __name__ == "__main__":
    mcp.run()
```

### Step 2: Register in opencode.json

```json
{
  "mcp": {
    "sdwan-tools": {
      "type": "local",
      "command": "python",
      "args": ["src/mcp_server.py"],
      "enabled": true
    },
    "thousandeyes-tools": {
      "type": "local",
      "command": "python",
      "args": ["src/te_mcp_server.py"],
      "enabled": true,
      "env": {
        "TE_API_TOKEN": "{env:TE_API_TOKEN}"
      }
    }
  }
}
```

### Step 3: Create Skill That Uses Both MCP Servers

```markdown
# File: .opencode/skills/circuit-health-analysis/SKILL.md

---
id: circuit-health-analysis
name: Circuit Health Analysis
description: Correlate SD-WAN and ThousandEyes data for ISP circuit diagnosis
author: Troubleshooting Team
version: 1.0
required_permissions:
  - read:devices
  - read:bfd
  - read:te
---

## Circuit Health Analysis

Diagnose ISP circuit issues by correlating SD-WAN BFD metrics with ThousandEyes circuit monitoring.

### MCP Tools Used

**From sdwan-tools**:
- get_bfd_sessions(system_ip)
- get_device_status(system_ip)

**From thousandeyes-tools**:
- get_network_tests()
- get_test_metrics(test_id)
- correlate_bfd_with_circuit(bfd_session, te_test_id)

### Workflow

1. Identify failing BFD session (system_ip, remote_ip, color)
2. Map BFD tunnel to TE test ID (via pre-configured mapping)
3. Get TE circuit metrics (latency, loss, jitter)
4. Correlate: Is circuit issue causing BFD flap?
5. Recommend: Escalate to ISP with evidence from both sources
```

---

## 5. Extension Checklist

When adding a new skill, tool, agent, or MCP server:

- [ ] **Naming**: Follows convention (verb_object, kebab-case)
- [ ] **Documentation**: Docstrings, README, examples
- [ ] **Testing**: Unit tests, integration tests, example prompts
- [ ] **Type Safety**: Type hints on all parameters/returns
- [ ] **Error Handling**: Structured error dicts, no exceptions to LLM
- [ ] **Permissions**: Declare required permissions in frontmatter
- [ ] **References**: Link to related skills/tools/docs
- [ ] **Version Control**: Commit with clear message
- [ ] **Integration**: Updated opencode.json, related skills
- [ ] **Performance**: No blocking calls; async where needed

---

## Roadmap: Phase 2 & 3 Extensions

### Phase 2 (Q2 2025)

**ThousandEyes Integration**
- Full circuit health correlation
- ISP SLA tracking
- Automated ISP escalation workflow

**Catalyst Center Integration** (Multi-Vendor)
- Fetch inventory from DNA Center
- Correlate SD-WAN + wired network
- Unified compliance reporting

**Advanced ML Anomaly Detection**
- Unsupervised learning on metrics
- Automatic anomaly alerts
- Predictive failure detection

### Phase 3 (Q3-Q4 2025)

**Multi-Vendor Support**
- Fortinet NGFW integration
- Juniper SRX integration
- VeloCloud API integration

**Self-Healing Automation**
- Auto-rollback on deployment errors
- Automated failover triggers
- Auto-remediation playbooks

**AI-Driven Policy Optimization**
- Analyze traffic patterns
- Recommend policy changes
- A/B test policies safely

---

## References

- [OpenCode Framework](https://opencode.ai/)
- [FastMCP Documentation](https://github.com/jlouns/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [ThousandEyes API Docs](https://docs.thousandeyes.com/product-documentation/integration-guides/thousandeyes-mcp-server)
- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
