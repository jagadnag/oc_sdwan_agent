# MCP Server Development Guide for SDWAN_AI

This guide covers building, testing, and extending the SDWAN_AI MCP servers. It assumes familiarity with Python and the Model Context Protocol (MCP).

---

## What is FastMCP?

**FastMCP** is a lightweight Python framework for building Model Context Protocol servers. It abstracts away JSON-RPC boilerplate and provides a simple decorator-based API for tool registration.

**Key Benefits**:
1. **Minimal overhead**: No complex initialization; tools are just Python functions
2. **Automatic schema generation**: Type hints become JSON Schema descriptions for LLMs
3. **Built-in error handling**: Exceptions are converted to structured error responses
4. **Stdio transport**: Works over stdin/stdout, making it portable

**Alternative frameworks**: Python MCP SDK (lower-level, more control), TypeScript MCP SDK (browser-based agents)

**Reference**: [FastMCP on GitHub](https://github.com/jlouns/fastmcp)

---

## SDWAN_AI MCP Server Architecture

```
opencode.json (config)
    ├─→ "mcp.sdwan-tools" -> python src/mcp_server.py
    └─→ "mcp.sastre-tools" -> python src/sastre_mcp_server.py (future)

src/mcp_server.py (FastMCP entry point)
    ├─→ Import and register tools
    ├─→ Initialize vManage client
    ├─→ Run MCP server on stdio
    └─→ Receive tool calls from OpenCode client

src/vmanage_client.py
    └─→ HTTP client for vManage REST API

src/collector.py
    └─→ High-level data collection + normalization

src/analyzers/
    ├─→ control_plane_analyzer.py
    ├─→ data_plane_analyzer.py
    ├─→ policy_analyzer.py
    └─→ alarm_analyzer.py

src/tools/
    ├─→ device_tools.py        (@mcp.tool functions for device ops)
    ├─→ health_tools.py        (@mcp.tool functions for health checks)
    ├─→ policy_tools.py        (@mcp.tool functions for policy)
    └─→ diagnostic_tools.py    (@mcp.tool functions for troubleshooting)
```

---

## FastMCP Basics

### Minimal Example

```python
from mcp.server.fastmcp import FastMCP
from typing import Optional

# Create MCP server instance
mcp = FastMCP("example-tools", "1.0.0")

# Register a tool with @mcp.tool decorator
@mcp.tool
def add_numbers(a: int, b: int) -> dict:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Dictionary with result
    """
    return {"result": a + b, "summary": f"{a} + {b} = {a + b}"}

@mcp.tool
def greet(name: str, greeting: Optional[str] = "Hello") -> str:
    """Greet someone.
    
    Args:
        name: Person's name
        greeting: Custom greeting (default: "Hello")
    
    Returns:
        Greeting message
    """
    return f"{greeting}, {name}!"

if __name__ == "__main__":
    # Run server on stdio
    mcp.run()
```

**How it works**:

1. OpenCode client calls MCP server with JSON-RPC:
   ```json
   {"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": "add_numbers", "arguments": {"a": 5, "b": 3}}}
   ```

2. FastMCP dispatcher matches tool name and calls `add_numbers(a=5, b=3)`

3. Result is wrapped and sent back:
   ```json
   {"jsonrpc": "2.0", "id": "1", "result": {"content": [{"type": "text", "text": "{\"result\": 8, ...}"}]}}
   ```

4. OpenCode client parses result and shows to LLM

---

## SDWAN_AI Tool Registration Pattern

### File Structure

```python
# src/mcp_server.py (entry point)

from mcp.server.fastmcp import FastMCP
from .vmanage_client import VManageClient
from .collector import SDWANCollector
from . import tools

# Initialize MCP server
mcp = FastMCP("sdwan-tools", "1.0.0")

# Initialize vManage client (singleton, reused across all tool calls)
vmanage_client = VManageClient(
    host=os.environ["VMANAGE_HOST"],
    user=os.environ["VMANAGE_USER"],
    password=os.environ["VMANAGE_PASSWORD"],
    verify_ssl=False  # Lab environment
)
vmanage_client.authenticate()

collector = SDWANCollector(vmanage_client)

# Import and auto-register all tools
# (tools are decorated with @mcp.tool in separate modules)
from .tools import device_tools, health_tools, policy_tools

if __name__ == "__main__":
    mcp.run()
```

### Tool Module Organization

```python
# src/tools/device_tools.py

import logging
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Import parent MCP instance (will be set by mcp_server.py)
mcp = None

def set_mcp_instance(mcp_instance):
    """Called by mcp_server.py to inject MCP and dependencies"""
    global mcp
    mcp = mcp_instance

@mcp.tool
def get_devices(
    device_type: Optional[str] = None,
    reachability: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """List all SD-WAN devices with optional filtering.
    
    Args:
        device_type: Filter by type: "vedges", "controllers", "vmanages"
        reachability: Filter by status: "reachable", "unreachable"
        limit: Results per page (max 10000)
        offset: Pagination offset
    
    Returns:
        Dictionary with device list and metadata
    """
    try:
        devices = mcp.vmanage_client.get_devices(limit=limit, offset=offset)
        
        # Apply client-side filtering
        if device_type:
            devices = [d for d in devices if d.get("device-type") == device_type]
        if reachability:
            devices = [d for d in devices if d.get("reachability") == reachability]
        
        return {
            "status": "success",
            "device_count": len(devices),
            "total_records": len(devices),
            "devices": devices,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_code": "device_fetch_failed"
        }

@mcp.tool
def get_device_health(system_ip: str) -> Dict[str, Any]:
    """Get detailed health status of a specific device.
    
    Args:
        system_ip: Device system IP (e.g., 10.0.50.1)
    
    Returns:
        Device health metrics (CPU, memory, connections, certs)
    """
    try:
        status = mcp.vmanage_client.get_device_status(system_ip)
        
        # Enrich with reachability and connectivity
        device_info = mcp.vmanage_client.get_device_info(system_ip)
        
        health = {
            "status": "success",
            "system_ip": system_ip,
            "hostname": device_info.get("hostname"),
            "reachability": status.get("reachability"),
            "cpu_percent": status.get("cpu-load", 0),
            "memory_percent": status.get("memory-percent", 0),
            "connected_vmanages": status.get("connected-vmanages", 0),
            "uptime_seconds": status.get("uptime", 0),
            "certificate_status": "valid" if status.get("certificates", {}).get("validity") == "valid" else "invalid",
            "certificate_expiry_epoch_ms": status.get("certificates", {}).get("expiration", None),
            "os_version": status.get("system", {}).get("os-version"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return health
    
    except Exception as e:
        logger.error(f"Failed to get device health for {system_ip}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_code": "device_health_failed",
            "system_ip": system_ip
        }
```

---

## Tool Naming Conventions

SDWAN_AI follows **verb_object** snake_case naming:

```python
# GOOD: verb_object naming
@mcp.tool
def get_devices(device_type: str = None) -> dict:
    pass

@mcp.tool
def get_control_plane_health() -> dict:
    pass

@mcp.tool
def get_alarms(severity_min: str = "warning") -> dict:
    pass

@mcp.tool
def validate_policy_attachment(template_id: str, devices: list) -> dict:
    pass

@mcp.tool
def attach_template(template_id: str, device_ids: list, dryrun: bool = True) -> dict:
    pass

# BAD: confusing names
@mcp.tool
def device_fetch():  # Use get_devices
    pass

@mcp.tool
def check_health():  # Which plane? Use get_control_plane_health, get_data_plane_health
    pass

@mcp.tool
def policy():  # Too vague; use get_policies, validate_policy, etc.
    pass
```

**Rationale**:
- LLMs understand verb_object better (mirrors English language)
- Easier to discover related tools (all "get_*", all "validate_*", etc.)
- CLI-like naming (consistent with kubectl, aws-cli)

---

## Type Hints & Docstrings

Type hints and docstrings are crucial: the LLM uses them to understand what each tool does.

### Type Hint Contract

```python
from typing import Optional, List, Dict, Any

@mcp.tool
def analyze_alarms(
    severity_min: str = "warning",           # Must include default if optional
    limit: int = 10,                         # Type must be Python built-in or stdlib
    time_window_hours: Optional[int] = None  # Use Optional[] for nullable
) -> Dict[str, Any]:                        # Return type MUST be provided
    """Analyze active alarms by severity.
    
    Args:
        severity_min: Minimum severity to include: "critical", "major", "minor", "warning"
        limit: Maximum alarms to return (1-1000)
        time_window_hours: Only include alarms in last N hours (None = all)
    
    Returns:
        Dictionary with alarm analysis:
        - status: "success" or "error"
        - alarm_count: Number of alarms
        - by_severity: Count by severity level
        - critical_alarms: List of critical alarms (if any)
        - timestamp: ISO timestamp of result
    """
    # Implementation
```

**Type Mapping**:

| Python Type | JSON Schema | LLM Understands |
|-------------|-----------|-----------------|
| `str` | `{"type": "string"}` | Text, URL, identifier |
| `int` | `{"type": "integer"}` | Number, count |
| `float` | `{"type": "number"}` | Decimal, percentage |
| `bool` | `{"type": "boolean"}` | True/False, yes/no |
| `List[str]` | `{"type": "array", "items": {"type": "string"}}` | Comma-separated, list |
| `Dict[str, Any]` | `{"type": "object"}` | Nested data |
| `Optional[str]` | `{"type": "string", "optional": true}` | Optional field |
| `Literal["a", "b"]` | `{"enum": ["a", "b"]}` | Choose from options |

### Docstring Best Practices

```python
@mcp.tool
def correlate_bfd_flaps(
    device_ip: str,
    include_events: bool = True
) -> Dict[str, Any]:
    """Diagnose BFD flap root cause and provide remediation.
    
    This tool correlates device-local BFD session state with control plane
    changes and interface errors to pinpoint the root cause of flapping tunnels.
    
    Args:
        device_ip: Device system IP (e.g., "10.0.50.1")
        include_events: Include vManage events in correlation (slower, more context)
    
    Returns:
        Dictionary containing:
        - root_cause: Likely root cause (e.g., "ISP circuit latency", "config mismatch")
        - confidence: Confidence level (0.0-1.0)
        - evidence: List of supporting evidence
        - recommendation: Next steps for remediation
        - investigation_time_ms: How long analysis took
        
        Example:
        {
            "root_cause": "BFD detection timer too aggressive",
            "confidence": 0.95,
            "evidence": [
                "BFD multiplier set to 1 (minimum is 3)",
                "Link latency stable at 50ms, no loss detected",
                "vSmart config unchanged in last 24h"
            ],
            "recommendation": "Increase BFD multiplier to 3-5 or decrease detect-interval",
            "investigation_time_ms": 245
        }
    
    Raises:
        VManageAPIError: If device is not reachable
    """
    # Implementation
```

**Docstring Format**:
1. **One-line summary**: What does this tool do?
2. **Detailed description**: Why would an architect use it? What problem does it solve?
3. **Args**: Parameter descriptions with types (even though Python already knows)
4. **Returns**: Return format + example structure
5. **Raises**: Exceptions the tool might raise

---

## Error Handling: Structured Returns

**Golden Rule**: Never raise exceptions to the LLM. Always return structured error responses.

### Pattern: Try/Catch with Structured Return

```python
@mcp.tool
def get_device_status(system_ip: str) -> Dict[str, Any]:
    """Get device status."""
    try:
        # Make API call
        status = mcp.vmanage_client.get_device_status(system_ip)
        
        # Validation
        if not status:
            return {
                "status": "error",
                "error": f"Device {system_ip} not found",
                "error_code": "device_not_found",
                "system_ip": system_ip
            }
        
        # Success response
        return {
            "status": "success",
            "system_ip": system_ip,
            "reachability": status.get("reachability"),
            "cpu_percent": status.get("cpu-load", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching status for {system_ip}")
        return {
            "status": "error",
            "error": "vManage API timeout (controller may be overloaded)",
            "error_code": "timeout",
            "system_ip": system_ip,
            "remediation": "Retry in 30 seconds; check vManage CPU/memory"
        }
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot reach vManage")
        return {
            "status": "error",
            "error": "Cannot reach vManage (network unreachable)",
            "error_code": "unreachable",
            "remediation": "Check vManage IP address and network connectivity"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "error_code": "internal_error"
        }
```

### Error Response Structure

```python
{
    "status": "error",
    "error": "Human-readable error message",
    "error_code": "machine_readable_code",
    "remediation": "Suggested next steps (optional)"
}
```

**Error Codes** (use consistently):
- `device_not_found`: Device doesn't exist in fabric
- `timeout`: API call timed out
- `unreachable`: Cannot reach vManage
- `auth_failed`: Authentication error
- `validation_failed`: Input validation error
- `internal_error`: Unexpected Python exception
- `policy_conflict`: Policy validation failed
- `insufficient_capacity`: Not enough resources

---

## Pagination for Large Result Sets

Many vManage endpoints return large datasets. Strategies:

### Strategy 1: Client-Side Pagination Loop

```python
@mcp.tool
def get_all_devices(device_type: Optional[str] = None) -> Dict[str, Any]:
    """Get all devices in fabric (handles pagination automatically)."""
    try:
        all_devices = []
        offset = 0
        limit = 100
        
        while True:
            resp = mcp.vmanage_client.get_devices(limit=limit, offset=offset)
            
            if not resp.get("data"):
                break
            
            all_devices.extend(resp["data"])
            
            # Check if we got less than limit (last page)
            if len(resp["data"]) < limit:
                break
            
            offset += limit
        
        # Filter if requested
        if device_type:
            all_devices = [d for d in all_devices if d.get("device-type") == device_type]
        
        return {
            "status": "success",
            "device_count": len(all_devices),
            "devices": all_devices,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### Strategy 2: Summarize Large Sets

When returning 1000+ items, LLM can't process all details. Summarize instead:

```python
@mcp.tool
def get_alarm_distribution(severity_min: str = "warning") -> Dict[str, Any]:
    """Get alarm distribution by severity (not the alarms themselves)."""
    try:
        # Fetch all alarms (paginated)
        all_alarms = []
        offset = 0
        
        while True:
            resp = mcp.vmanage_client.get_alarms(limit=500, offset=offset, severity=severity_min)
            if not resp.get("data"):
                break
            all_alarms.extend(resp["data"])
            if len(resp["data"]) < 500:
                break
            offset += 500
        
        # Summarize instead of returning all
        distribution = {}
        by_device = {}
        
        for alarm in all_alarms:
            sev = alarm.get("severity", "unknown")
            distribution[sev] = distribution.get(sev, 0) + 1
            
            dev = alarm.get("hostname", "unknown")
            by_device[dev] = by_device.get(dev, 0) + 1
        
        return {
            "status": "success",
            "total_alarms": len(all_alarms),
            "by_severity": distribution,
            "top_devices": sorted(by_device.items(), key=lambda x: x[1], reverse=True)[:10],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

---

## Adding a New Tool: 5-Step Workflow

### Step 1: Define the Tool Interface

What should the LLM be able to ask? Write the function signature first:

```python
@mcp.tool
def diagnose_bfd_flap(
    system_ip: str,
    remote_ip: str,
    color: str = "public",
    include_historical_data: bool = False
) -> Dict[str, Any]:
    """Diagnose BFD session flapping and recommend remediation.
    
    Use this tool when a BFD tunnel is unstable (state changes frequently).
    """
    pass
```

### Step 2: Write the Docstring

Be explicit about inputs, outputs, and use case:

```python
@mcp.tool
def diagnose_bfd_flap(
    system_ip: str,
    remote_ip: str,
    color: str = "public",
    include_historical_data: bool = False
) -> Dict[str, Any]:
    """Diagnose BFD session flapping and recommend remediation.
    
    When a BFD session is flapping (state changing frequently), this tool
    correlates device-local metrics (latency, loss, jitter) with control plane
    changes to pinpoint whether the issue is ISP circuit health, vSD-WAN config,
    or hardware capacity.
    
    Args:
        system_ip: Local device system IP (e.g., "10.0.50.1")
        remote_ip: Remote device system IP (e.g., "10.1.1.1")
        color: TLOC color (public, private, metro-ethernet, mpls, 3g, lte)
        include_historical_data: Fetch data from last 24h (slower)
    
    Returns:
        {
            "status": "success",
            "root_causes": [
                {"cause": "BFD multiplier too low", "confidence": 0.95},
                {"cause": "ISP latency spike", "confidence": 0.80}
            ],
            "current_metrics": {
                "bfd_state": "down",
                "flap_count": 7,
                "latency_ms": 150,
                "loss_percent": 2.5,
                "jitter_ms": 45
            },
            "recommendations": [
                "Increase BFD multiplier from 1 to 3",
                "Check ISP BGP path for alternate route"
            ]
        }
    """
    pass
```

### Step 3: Collect Required Data

Gather all data needed for analysis:

```python
def diagnose_bfd_flap(system_ip: str, remote_ip: str, color: str = "public", include_historical_data: bool = False) -> Dict[str, Any]:
    """..."""
    try:
        # Fetch BFD session state
        bfd_sessions = mcp.vmanage_client.get_bfd_sessions(system_ip)
        target_session = next(
            (s for s in bfd_sessions if s.get("peer-system-ip") == remote_ip and s.get("color") == color),
            None
        )
        
        if not target_session:
            return {
                "status": "error",
                "error": f"BFD session not found ({system_ip} -> {remote_ip}/{color})",
                "error_code": "bfd_session_not_found"
            }
        
        # Fetch device metrics
        device_status = mcp.vmanage_client.get_device_status(system_ip)
        interfaces = mcp.vmanage_client.get_interface_stats(system_ip)
        
        # Fetch control plane state
        control_conns = mcp.vmanage_client.get_control_connections(system_ip)
        
        # Optional: historical data
        recent_events = []
        if include_historical_data:
            recent_events = mcp.vmanage_client.get_events(
                device_ip=system_ip,
                time_window_hours=24
            )
        
        # Now we have all the data we need...
```

### Step 4: Analyze & Synthesize

Apply domain logic to produce insights:

```python
        # Analyze current state
        root_causes = []
        confidence_scores = {}
        
        # Heuristic 1: Low BFD multiplier
        bfd_multiplier = target_session.get("multiplier", 3)
        if bfd_multiplier == 1:
            root_causes.append("BFD multiplier too low (minimum 3 recommended)")
            confidence_scores["low_multiplier"] = 0.95
        
        # Heuristic 2: High latency + loss
        latency = target_session.get("latency", 0)
        loss = target_session.get("loss-percent", 0)
        if latency > 100 and loss > 1.0:
            root_causes.append("ISP circuit latency/loss spike")
            confidence_scores["circuit_issue"] = 0.80
        
        # Heuristic 3: Device CPU overloaded
        cpu = device_status.get("cpu-load", 0)
        if cpu > 85:
            root_causes.append("Device CPU overloaded (may cause BFD miss detection)")
            confidence_scores["cpu_overload"] = 0.70
        
        # Generate recommendations
        recommendations = []
        if "low_multiplier" in confidence_scores:
            recommendations.append("Increase BFD multiplier to 3-5 (config dependent)")
        if "circuit_issue" in confidence_scores:
            recommendations.append("Contact ISP; monitor circuit with ThousandEyes")
        if "cpu_overload" in confidence_scores:
            recommendations.append("Redistribute traffic or upgrade device")
        
        return {
            "status": "success",
            "system_ip": system_ip,
            "remote_ip": remote_ip,
            "root_causes": root_causes,
            "confidence_scores": confidence_scores,
            "current_metrics": {
                "bfd_state": target_session.get("state"),
                "flap_count": target_session.get("flap-count", 0),
                "latency_ms": latency,
                "loss_percent": loss,
                "jitter_ms": target_session.get("jitter", 0),
                "uptime_seconds": target_session.get("uptime", 0)
            },
            "device_metrics": {
                "cpu_percent": cpu,
                "memory_percent": device_status.get("memory-percent", 0),
                "uptime_seconds": device_status.get("uptime", 0)
            },
            "recommendations": recommendations,
            "investigation_time_ms": int((time.time() - start_time) * 1000)
        }
```

### Step 5: Error Handling

Wrap in try/catch:

```python
    except KeyError as e:
        logger.error(f"Missing field in API response: {e}")
        return {
            "status": "error",
            "error": f"Incomplete API response: {str(e)}",
            "error_code": "api_response_incomplete",
            "remediation": "Retry or check vManage version compatibility"
        }
    
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error": "vManage API timeout",
            "error_code": "timeout",
            "remediation": "vManage may be overloaded; retry in 30 seconds"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in diagnose_bfd_flap: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_code": "internal_error"
        }
```

---

## Testing Tools with pytest

### Setup

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Create test file: tests/test_device_tools.py
```

### Test Template

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.tools.device_tools import get_devices, get_device_health
from src.vmanage_client import VManageClient, VManageAPIError

@pytest.fixture
def mock_vmanage_client():
    """Mock vManage client for testing"""
    client = Mock(spec=VManageClient)
    return client

@pytest.fixture
def mock_collector(mock_vmanage_client):
    """Mock collector with injected vManage client"""
    collector = Mock()
    collector.vmanage_client = mock_vmanage_client
    return collector

def test_get_devices_success(mock_vmanage_client, mock_collector):
    """Test get_devices returns device list"""
    # Setup mock response
    mock_vmanage_client.get_devices.return_value = {
        "data": [
            {
                "deviceId": "192.168.1.1",
                "uuid": "device-uuid-1",
                "hostname": "hub-1",
                "device-type": "vsmarts",
                "reachability": "reachable",
                "status": "normal"
            }
        ],
        "totalRecords": 1
    }
    
    # Inject mock into tool
    with patch("src.tools.device_tools.mcp") as mock_mcp:
        mock_mcp.vmanage_client = mock_vmanage_client
        
        result = get_devices(limit=10, offset=0)
    
    # Verify result
    assert result["status"] == "success"
    assert result["device_count"] == 1
    assert result["devices"][0]["hostname"] == "hub-1"

def test_get_devices_filters_by_type(mock_vmanage_client):
    """Test device type filtering"""
    mock_vmanage_client.get_devices.return_value = {
        "data": [
            {"hostname": "hub-1", "device-type": "vsmarts"},
            {"hostname": "spoke-1", "device-type": "vedges"}
        ],
        "totalRecords": 2
    }
    
    with patch("src.tools.device_tools.mcp") as mock_mcp:
        mock_mcp.vmanage_client = mock_vmanage_client
        
        result = get_devices(device_type="vsmarts")
    
    assert result["status"] == "success"
    assert result["device_count"] == 1
    assert result["devices"][0]["hostname"] == "hub-1"

def test_get_devices_handles_api_error(mock_vmanage_client):
    """Test error handling when API call fails"""
    mock_vmanage_client.get_devices.side_effect = VManageAPIError("Connection timeout")
    
    with patch("src.tools.device_tools.mcp") as mock_mcp:
        mock_mcp.vmanage_client = mock_vmanage_client
        
        result = get_devices()
    
    assert result["status"] == "error"
    assert "error" in result
    assert result["error_code"] == "device_fetch_failed"

def test_get_device_health_success(mock_vmanage_client):
    """Test get_device_health returns health metrics"""
    mock_vmanage_client.get_device_status.return_value = {
        "hostname": "vedge-site5",
        "reachability": "reachable",
        "cpu-load": 25.5,
        "memory-percent": 62.3,
        "connected-vmanages": 1,
        "uptime": 18574800,
        "certificates": {
            "validity": "valid",
            "expiration": 1735689600000
        },
        "system": {"os-version": "19.2.1"}
    }
    mock_vmanage_client.get_device_info.return_value = {
        "hostname": "vedge-site5"
    }
    
    with patch("src.tools.device_tools.mcp") as mock_mcp:
        mock_mcp.vmanage_client = mock_vmanage_client
        
        result = get_device_health("10.0.50.1")
    
    assert result["status"] == "success"
    assert result["cpu_percent"] == 25.5
    assert result["memory_percent"] == 62.3
    assert result["certificate_status"] == "valid"

# Run tests
# pytest tests/test_device_tools.py -v
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_device_tools.py -v

# Run specific test
pytest tests/test_device_tools.py::test_get_devices_success -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run with logging
pytest tests/ -v --log-cli-level=INFO
```

---

## Comparison with ThousandEyes MCP Server

| Aspect | SDWAN_AI | ThousandEyes |
|--------|----------|-------------|
| **FastMCP Usage** | Yes (Python decorator pattern) | Yes (similar structure) |
| **Tool Count** | ~20-30 (device, health, policy, diagnostic) | ~15 (test management, metrics) |
| **Caching Strategy** | 5-min TTL in collector layer | Server-side (TE handles caching) |
| **Error Handling** | Structured dicts with error_code | HTTP status codes + error messages |
| **Mutation Support** | Yes (dryrun + approval) | No (read-only) |
| **Testing Approach** | pytest with mocked vManage client | pytest with mocked TE API |
| **Documentation** | Tool docstrings + API_REFERENCE.md | Tool docstrings + TE docs reference |

**Key Similarity**: Both use FastMCP's @mcp.tool decorator pattern, making them easy to discover and maintain.

---

## Best Practices Checklist

- [ ] **Naming**: All tools use verb_object snake_case (get_*, validate_*, attach_*)
- [ ] **Type Hints**: All parameters and return types are annotated
- [ ] **Docstrings**: Every tool has Args, Returns, and use case description
- [ ] **Error Handling**: No exceptions raised to LLM; all errors in structured dicts
- [ ] **Pagination**: Large result sets paginated or summarized
- [ ] **Testing**: All tools have unit tests with mocked dependencies
- [ ] **Logging**: Important operations logged at INFO; errors at ERROR
- [ ] **Performance**: API calls cached where appropriate; heavy operations report timing
- [ ] **Extensibility**: Tools organized by domain (device_tools, policy_tools, etc.)
- [ ] **Comments**: Complex heuristics documented (e.g., flap detection algorithm)

---

## References

- [FastMCP GitHub](https://github.com/jlouns/fastmcp)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [ThousandEyes MCP Server](https://docs.thousandeyes.com/product-documentation/integration-guides/thousandeyes-mcp-server)
- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
