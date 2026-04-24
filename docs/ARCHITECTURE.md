# SDWAN_AI Architecture Guide

## Overview

SDWAN_AI is a standalone MVP "Cisco SD-WAN AI sidekick" agent for CCIE-certified SD-WAN architects and operators. It combines the OpenCode framework with FastMCP protocol to provide intelligent, agentic access to Cisco SD-WAN Manager (vManage) REST API and Sastre CLI, enabling rapid diagnosis, design validation, and operational automation across large-scale SD-WAN fabrics.

The architecture is inspired by two reference models:
- **BRKENT-2215**: Cisco Live AI Troubleshooting Agent (LLM + infrastructure separation via protocol)
- **ThousandEyes MCP Server**: Modern MCP server design patterns for observability platforms

---

## System Architecture Diagram

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│  Architect   │   │  Operator    │   │ Trouble-     │   │  Mobile/Partner  │
│  (Human)     │   │  (Human)     │   │  shooter     │   │  Access (Future) │
└───────┬──────┘   └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘
        │                 │                  │                     │
        └─────────────────┼──────────────────┼─────────────────────┘
                          │
                ┌─────────▼──────────┐
                │  OpenCode Client   │
                │ (LibreChat/Browser)│
                │  Multi-Agent Loop  │
                │  Agent: architect  │
                │  Agent: operator   │
                │  Agent: trouble-   │
                │         shooter    │
                └─────────┬──────────┘
                          │
         ┌────────────────┼────────────────┐
         │   MCP Protocol (JSON-RPC)      │
         └────────────────┼────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
    ┌────▼─────────────┐          ┌───────▼────────┐
    │  MCP Server 1    │          │  MCP Server 2  │
    │  sdwan-tools     │          │  sastre-tools  │
    │ (vManage REST)   │          │  (CLI wrap)    │
    │                  │          │                │
    │ Tools:           │          │ Tools:         │
    │ - get_devices    │          │ - backup_cfg   │
    │ - get_alarms     │          │ - restore_cfg  │
    │ - get_stats      │          │ - dryrun_apply │
    │ - get_templates  │          │ - list_images  │
    │ - validate_*     │          │ - verify_certs │
    │                  │          │                │
    └────┬─────────────┘          └───────┬────────┘
         │                               │
    ┌────▼────────────────────────────────▼──────────┐
    │                                                 │
    │  ┌──────────────┐   ┌──────────────┐           │
    │  │  vManage API │   │ Sastre CLI   │           │
    │  │ /dataservice │   │ subprocess   │           │
    │  │              │   │              │           │
    │  │ - device     │   │ - import/    │           │
    │  │ - alarms     │   │   export     │           │
    │  │ - templates  │   │ - merge/     │           │
    │  │ - statistics │   │   transform  │           │
    │  │ - policy     │   │ - attach/    │           │
    │  │              │   │   detach     │           │
    │  └──────────────┘   └──────────────┘           │
    │                                                 │
    │  SD-WAN Fabric                                 │
    │  (vBond, vManage, vSmart, edges)               │
    │                                                 │
    └─────────────────────────────────────────────────┘
```

---

## Why MCP Architecture?

The Model Context Protocol (MCP) provides a **clean separation of concerns** between the large language model (Claude) and infrastructure-specific tools. This design pattern has three critical advantages:

1. **LLM-agnostic**: MCP tools work with any LLM (Claude, GPT, Gemini, etc.) without re-implementation
2. **Composable**: Multiple MCP servers (vManage, Sastre, future ThousandEyes, Catalyst Center) coexist without conflict
3. **Safe by default**: LLM cannot directly execute code; it can only invoke registered tools with specific schemas
4. **Observable**: All tool invocations are logged; audit trail is built-in

This mirrors the architecture of the ThousandEyes MCP server, which isolates API calls behind a well-defined tool interface, preventing prompt injection attacks and enabling fine-grained access control.

---

## Three Personas

SDWAN_AI operates with three distinct personas, each with tailored prompts and permission models. They share the same MCP tools but approach problems differently:

### 1. sdwan-architect

**User Profile**: CCIE-certified SD-WAN architect with 10+ years experience. Responsible for topology design, policy models, capacity planning, security posture.

**Typical Tasks**:
- Design a new overlay topology (hub-and-spoke, hub-hub, partial mesh)
- Recommend control policy and traffic engineering strategy
- Validate policy attachment before bulk deployment
- Plan quarterly software upgrades
- Design zero-trust segmentation (VPN + firewall policy)

**Permission Model**:
- vManage API: read-only (all /dataservice/* GET endpoints)
- Bash: ask-before-run (architect may request dryrun of Sastre commands)
- Edit: deny (no direct file editing)
- WebFetch: deny (no arbitrary web access)

**Workflow**: Gather data → analyze → recommend → validate → hand off to operator for deployment

### 2. sdwan-troubleshooter

**User Profile**: CCIE support engineer or network architect responding to incidents. Responsible for rapid diagnosis and escalation.

**Typical Tasks**:
- Triage and root-cause alarms (BFD flaps, control plane down, AppRoute failures)
- Investigate intermittent data plane issues (packet loss, latency spikes)
- Correlate events across control, data, and orchestration planes
- Snapshot device state before escalation to TAC

**Permission Model**:
- vManage API: read-only
- Bash: ask-before-run (limited to diagnostic CLI, not mutations)
- Edit: deny
- WebFetch: deny

**Workflow**: Collect symptomatic data → isolate root cause → validate hypothesis → escalate with context

### 3. sdwan-operator

**User Profile**: NOC engineer responsible for daily operations, deployments, and change management.

**Typical Tasks**:
- Execute pre-planned template/policy deployments
- Monitor fabric health and respond to routine alarms
- Perform configuration snapshots (backup/restore)
- Validate configuration changes against snapshot diffs
- Execute onboarding checklist for new sites

**Permission Model**:
- vManage API: read-only
- Bash: ask-before-run (Sastre dryrun must be confirmed before apply)
- Edit: deny
- WebFetch: deny

**Workflow**: Pre-flight check → staged dryrun → human approval → deployment → post-flight validation

---

## Component Architecture

### Data Flow Layers

```
User Prompt
    ↓
OpenCode Agent Loop
    ├─→ System Prompt (persona)
    ├─→ Tool Available (MCP tools)
    ├─→ Tool Results (structured data)
    └─→ Reasoning & Response
    ↓
LLM Decision
    ├─→ Call tool? (which one, with what params?)
    └─→ Respond to user?
    ↓
MCP Tool Invocation
    ├─→ Validate input schema
    ├─→ Execute (vManage API or Sastre CLI)
    ├─→ Format result
    └─→ Return to LLM
    ↓
Structured Data (JSON)
    └─→ Back to Agent Loop
```

### MCP Server: sdwan-tools

**Location**: `src/mcp_server.py`

**Purpose**: Wraps vManage REST API in MCP tool interface. Handles authentication, pagination, error recovery, and caching.

**Key Components**:

1. **VManageClient** (`src/vmanage_client.py`)
   - HTTP session management with connection pooling
   - Token-based authentication (vManage 20.x+)
   - JSESSIONID fallback (vManage 15.x)
   - Retry strategy (exponential backoff on 503, 504)
   - SSL/TLS handling

2. **SDWANCollector** (`src/collector.py`)
   - High-level collection methods (fabric overview, control plane health, data plane health)
   - Caching layer (5-minute TTL default)
   - Multi-call enrichment (combine /device + /system status for complete picture)
   - Normalization to consistent schemas

3. **Analyzers** (`src/analyzers/`)
   - `alarm_analyzer.py`: Severity categorization, correlation heuristics
   - `control_plane_analyzer.py`: OMP peer state, TLOC preference, BFD health
   - `data_plane_analyzer.py`: IPsec tunnel state, BFD flap detection, packet loss anomalies
   - `policy_analyzer.py`: Policy attachment validation, rule conflict detection

4. **Tool Handlers** (`src/tools/`)
   - Each tool is a Python function decorated with `@mcp.tool`
   - Type hints and docstrings define the LLM interface
   - Structured error returns (never raise exceptions to LLM)

### MCP Server: sastre-tools (Future/Optional)

**Purpose**: Wraps Cisco DevNet Sastre CLI in MCP tool interface for bulk configuration operations.

**Tools**:
- `backup_configuration(description, device_groups)`
- `restore_configuration(backup_id, dryrun=True)`
- `list_backups()`
- `attach_template(template_id, device_ids, dryrun=True)`
- `detach_template(template_id, device_ids, dryrun=True)`
- `list_device_images()`
- `verify_certificates()`

---

## Data Flow Walkthrough: "Morning Health Check"

**Trigger**: Scheduled 8am (Eastern) weekday

**Workflow**:

```
1. LLM (sdwan-architect persona) receives prompt:
   "Run morning health check: fabric overview, control plane, data plane, top 5 alarms"

2. Agent invokes tools in sequence:
   - get_fabric_overview()
     → Returns: devices[], reachable_count, unreachable_count, timestamp
   
   - get_control_plane_health()
     → Returns: control_connections[], omp_peers[], healthy_count, down_count
   
   - get_data_plane_health()
     → Returns: bfd_sessions[], up_count, down_count, flapping_count
   
   - get_alarms(limit=5, severity_min='critical')
     → Returns: alarm[], severity_distribution, last_cleared_time

3. LLM receives structured results from all tools

4. LLM (using prompt instructions) synthesizes findings:
   - Checks against thresholds (e.g., >5% unreachable devices = issue)
   - Correlates data plane flaps with control plane changes
   - Highlights critical alarms with context
   - Recommends next action (investigate specific site, call architect, etc.)

5. Response to user:
   "Fabric is HEALTHY. 145 devices reachable, 3 unreachable (vEdge-DC2, vEdge-SiteA-3, vEdge-Backhaul-1).
    All 15 vSmarts reporting OMP. 2 BFD sessions flapping (Site-5 <-> Hub-2). 
    Alarm: Control connection down at Site-7 [CRITICAL] - likely bandwidth constraint.
    Recommendation: Investigate Site-7 ISP connection; site may exceed SLA next report."

6. Audit log entry:
   timestamp=2025-01-15T08:00:05Z
   agent=sdwan-architect
   user=alice@company.com
   tools_invoked=[get_fabric_overview, get_control_plane_health, get_data_plane_health, get_alarms]
   result_summary="Fabric healthy, 3 unreachable, 2 BFD flaps, 1 critical alarm"
```

---

## Security Model

SDWAN_AI enforces **defense-in-depth** security:

### Read-Only by Default

All MCP tools default to read-only vManage API calls:
- GET /dataservice/* allowed
- POST /dataservice/template/*/attach* denied unless explicit approval
- POST /dataservice/device/action/* denied unless explicit approval
- Bash commands blocked unless architect/operator confirms

### Mutation Gates

For any destructive or configuration-changing operation:

1. **Dryrun Preview**: Sastre/CLI always runs with --dryrun flag first
2. **Diff Display**: Show the exact changes before approval
3. **Human Approval**: User explicitly types "yes, apply" (not just a button click)
4. **Audit Log**: Record who approved what, when, and what changed

**Example**: Attaching a device template to 50 edge routers

```
User: "Attach template 'DC-Site-Template' to DC2 site (10 devices)"

Agent Response (dryrun):
"Dryrun preview: Will modify configuration on 10 devices:
 - vEdge-DC2-1: IP 192.168.1.1 → 10.0.1.1
 - vEdge-DC2-2: IP 192.168.1.2 → 10.0.2.1
 [... 8 more ...]
 
Estimated sync time: 2-3 minutes. Device reachability will be maintained during template attachment.

Should I proceed? (yes/no)"

User: "yes"

Agent (real apply):
"Attaching template... Monitoring sync status...
vEdge-DC2-1: ✓ sync'd (1m 2s)
vEdge-DC2-2: ✓ sync'd (1m 15s)
[... 8 more ...]
All 10 devices successfully synchronized."
```

### Credential Handling

- vManage credentials sourced from environment variables or `.env` file
- Never logged or displayed in responses
- Session token cached in memory; regenerated if expired
- HTTPS/TLS enforced; SSL verification can be disabled for lab environments only

### RBAC & Audit Trail

- Each tool invocation logged with:
  - Timestamp (UTC)
  - User identity (from OpenCode context)
  - Agent persona used
  - Tool name and parameters
  - Result summary (not sensitive data)
- Logs stored in `logs/sdwan_ai.log` and rotated daily
- Can be shipped to SIEM (Splunk, ELK) for compliance

---

## Extension Pattern: Adding a New MCP Server

Example: Integrating ThousandEyes API for ISP circuit monitoring

### Step 1: Create MCP Server File

```bash
# File: src/te_mcp_server.py

from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("thousandeyes-tools", "1.0.0")

@mcp.tool
def get_network_tests(test_type: str = "http-server"):
    """List all ThousandEyes network tests (http-server, dns, bgp, etc.)"""
    # Call TE API
    tests = requests.get(
        "https://api.thousandeyes.com/v7/tests",
        headers={"Authorization": f"Bearer {os.environ['TE_API_TOKEN']}"}
    ).json()
    return {"tests": tests, "count": len(tests)}

@mcp.tool
def get_test_metrics(test_id: str, metric: str = "latency"):
    """Get latest metrics for a specific test (latency, loss, jitter)"""
    # Implementation
    pass

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
      "args": ["src/mcp_server.py"]
    },
    "thousandeyes-tools": {
      "type": "local",
      "command": "python",
      "args": ["src/te_mcp_server.py"],
      "env": {
        "TE_API_TOKEN": "{env:TE_API_TOKEN}"
      }
    }
  }
}
```

### Step 3: Update Agent Prompts

Add TE context to architect persona:

```markdown
## Available Tools: ThousandEyes Integration

You now have access to real-time ISP circuit health from ThousandEyes:
- get_network_tests(): List all TE tests (carrier links, peering, DDoS scrubbing centers)
- get_test_metrics(test_id): Latency, loss, jitter, TCP connect time, DNS resolution time

When troubleshooting data plane issues:
1. First check vManage BFD/IPsec state (vManage tools)
2. Then check TE circuit health (TE tools)
3. Correlate: if TE shows high latency but BFD is up → ISP congestion (not tunnel issue)
4. Recommend: escalate to ISP ticket, temporarily steer traffic via backup carrier
```

### Step 4: Design Analyzers

Create `src/analyzers/te_analyzer.py` to correlate TE + SD-WAN data:

```python
def correlate_bfd_and_circuit_health(bfd_session, te_test_metrics):
    """
    Diagnose BFD flaps by correlating with ThousandEyes circuit data.
    
    Returns:
    {
      "root_cause": "ISP circuit latency spike" | "vSD-WAN config" | "tunnel encap loss",
      "evidence": [...],
      "recommendation": "..."
    }
    """
    if te_test_metrics["latency_ms"] > 200 and bfd_session["flap_count"] > 10:
        return {
            "root_cause": "ISP circuit latency spike",
            "evidence": [
                f"TE circuit latency: {te_test_metrics['latency_ms']}ms (baseline 50ms)",
                f"BFD flaps in last 5min: {bfd_session['flap_count']}"
            ],
            "recommendation": "Contact ISP; monitor TE circuit for resolution; consider failover to backup carrier"
        }
```

---

## Comparison with ThousandEyes MCP Server

| Aspect | SDWAN_AI | ThousandEyes MCP |
|--------|----------|-----------------|
| **Domain** | Cisco SD-WAN (vManage API) | ISP/carrier circuit monitoring |
| **Primary Data Source** | REST API (`/dataservice/*`) | REST API (`api.thousandeyes.com/v7`) |
| **Mutation Support** | Yes (template/policy attach, with dryrun + approval gate) | No (read-only observability) |
| **Authentication** | Session token (vManage), env var (Sastre) | Bearer token (TE API) |
| **Caching Strategy** | 5-minute TTL + LRU eviction | Query-time caching (TE server-side) |
| **Extension Pattern** | Add MCP server + update opencode.json | Add MCP server + update opencode.json |
| **Error Handling** | Structured error dicts to LLM | HTTP status + error message |
| **Analyzer Pattern** | Multiple analyzers (control plane, data plane, etc.) | Metric-based alerts + API response parsing |

---

## Component Deep Dives

### vManage REST API Integration

The VManageClient handles the low-level HTTP plumbing:

```python
# Authentication flow
client = VManageClient(
    host="192.168.1.10",
    user="admin",
    password="Cisco123!",
    verify_ssl=False  # Lab only
)
client.authenticate()  # Token-based or JSESSIONID

# Authenticated requests include:
# - Cookie: JSESSIONID (if older vManage)
# - Header: X-XSRF-TOKEN (CSRF protection)
# - Header: Authorization: Bearer <token> (if 20.x+)

# Pagination for large result sets
devices = client.get_devices(limit=100, offset=0)
# Returns: {"data": [...], "totalRecords": 500}

# Next 100
devices = client.get_devices(limit=100, offset=100)
```

### Collector: Multi-Call Enrichment

Some insights require combining multiple API calls:

```python
def collect_fabric_overview():
    # Call 1: Get device list
    devices = client.get_devices()  # Basic info
    
    # Call 2: For each device, get detailed status
    for device in devices:
        status = client.get_device_status(device["uuid"])
        device["reachability"] = status.get("status")
        device["system_info"] = status.get("system")
    
    # Call 3: Aggregate
    reachable = sum(1 for d in devices if d["reachability"] == "reachable")
    
    # Return enriched, normalized view
    return {
        "devices": devices,
        "reachable_count": reachable,
        "unreachable_count": len(devices) - reachable,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

### Analyzers: Domain Logic

Analyzers take structured data and apply SD-WAN-specific heuristics:

```python
class ControlPlaneAnalyzer:
    def diagnose_omp_peer_down(self, peer):
        """Given a down OMP peer, suggest root cause"""
        # Heuristics:
        # 1. Is vSmart device reachable? (check against device list)
        # 2. Are control connections up? (check control connection state)
        # 3. Is this a known planned maintenance window? (check events)
        # 4. Has peer been flapping? (check recent state changes)
        
        if not device_reachable(peer["vsmart_id"]):
            return "vSmart unreachable (device down or network isolation)"
        elif control_conns_down():
            return "All control connections down (fabric partition)"
        else:
            return "Isolated OMP peer failure (check vSmart logs)"
```

---

## Operational Workflows

Each SDWAN_AI persona has standard workflows (see DAILY_WORKFLOWS.md for detailed playbooks):

### Architect Workflow: Pre-Change Validation

```
1. Gather current state (snapshot)
   - Template attachment graph
   - Policy enforcement rules
   - Device group membership
   - Recent change audit trail

2. Analyze impact
   - Which devices affected?
   - What policies change?
   - Risk assessment (critical/high/medium)

3. Validate against best practices
   - Is this topology compatible with fabric scale?
   - Does policy follow least-privilege principle?
   - Are OMP attributes correctly set?

4. Recommend
   - Proceed as-is
   - Modify and re-validate
   - Request additional data (e.g., circuit capacities)

5. Hand off to operator
   - Dryrun snapshot
   - Approval checklist
   - Rollback plan
```

### Troubleshooter Workflow: Alarm Triage

```
1. Collect symptomatic data
   - Alarms (severity, time, device, message)
   - Related events (template changes, link flaps)
   - Device/control/data plane state

2. Correlate
   - Is this a symptom or root cause?
   - What else changed recently?
   - Are similar alarms on other devices?

3. Hypothesize
   - Top-3 likely root causes (with evidence)

4. Investigate
   - Run targeted diagnostics to confirm hypothesis

5. Escalate or resolve
   - If root cause found → provide recommendation
   - If unclear → snapshot state + hand off to architect/TAC
```

### Operator Workflow: Change Deployment

```
1. Pre-flight check
   - Device health check
   - Backup snapshot
   - Capacity review

2. Dryrun
   - Apply change with --dryrun flag
   - Display diff
   - Get human approval

3. Deploy
   - Apply change (real)
   - Monitor device sync status
   - Check for errors

4. Post-flight validation
   - Compare new state vs pre-flight snapshot
   - Run health check
   - Document change in runbook
```

---

## Logging & Observability

SDWAN_AI logs all tool invocations for audit and debugging:

**Log Format** (structured JSON):

```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "level": "INFO",
  "logger": "sdwan_ai.mcp_server",
  "message": "Tool invoked",
  "tool_name": "get_alarms",
  "tool_params": {
    "limit": 5,
    "severity_min": "critical"
  },
  "result_summary": "5 critical alarms retrieved",
  "agent": "sdwan-architect",
  "user": "alice@company.com",
  "duration_ms": 245
}
```

**Log Destinations**:
- Local: `logs/sdwan_ai.log` (rotating, daily)
- Optional: Splunk, ELK, CloudWatch (configure via env var `LOG_BACKEND`)

**Metrics** (exposed for monitoring):
- Tool invocation count by name
- Tool execution time (p50, p95, p99)
- API response times to vManage
- Cache hit rate
- Error rate by tool

---

## Security Best Practices

1. **Separate Credentials**: vManage + Sastre creds in different env vars or Vault
2. **Network Isolation**: MCP server should run on same network as vManage (no internet exposure)
3. **SSL Verification**: In production, verify vManage SSL certificate (not `verify_ssl=False`)
4. **Rate Limiting**: MCP server should throttle vManage API requests to avoid controller overload
5. **Least Privilege**: vManage user account should have minimal necessary permissions
6. **Audit Logging**: Integrate with SIEM; alert on unusual tool usage patterns

---

## Roadmap & Future Extensions

### Phase 1 (Current MVP)
- vManage REST API integration
- Sastre CLI wrapping (dryrun-only in MVP)
- Three personas (architect, troubleshooter, operator)
- Daily health checks + alarm triage

### Phase 2 (Planned)
- ThousandEyes MCP server (circuit monitoring)
- Cisco Catalyst Center (multi-vendor ops center)
- Advanced ML-based anomaly detection
- Predictive capacity planning

### Phase 3 (Future)
- Multi-vendor support (Fortinet, Juniper, VeloCloud)
- Self-healing automation (auto-rollback on errors)
- AI-driven policy optimization
- Integration with Slack/PagerDuty for incident response

---

## References

- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
- [Cisco Live BRKENT-2215: AI Troubleshooting Agent](https://www.ciscolive.com/)
- [Cisco Live BRKENT-3797: Policy Troubleshooting](https://www.ciscolive.com/)
- [Cisco Live BRKSEC-2708: Security in SD-WAN](https://www.ciscolive.com/)
- [ThousandEyes MCP Server](https://docs.thousandeyes.com/product-documentation/integration-guides/thousandeyes-mcp-server)
- [OpenCode Framework](https://opencode.ai/)
- [FastMCP: Fast Model Context Protocol](https://github.com/jlouns/fastmcp)
