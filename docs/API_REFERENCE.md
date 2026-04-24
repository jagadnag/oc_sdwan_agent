# Cisco SD-WAN Manager REST API Reference

This document covers the vManage REST API endpoints used by SDWAN_AI, organized by functional category. All endpoints are relative to the vManage base URL (e.g., `https://192.168.1.10:443/dataservice/`).

**Reference**: [Cisco SD-WAN API Documentation](https://developer.cisco.com/docs/sdwan/)

---

## Authentication

### POST /j_security_check

Legacy authentication endpoint (vManage 15.x-16.x). Used for obtaining JSESSIONID cookie.

**Method**: POST

**Path**: `/j_security_check`

**Request**:
```json
{
  "j_username": "admin",
  "j_password": "Cisco123!"
}
```

**Response** (on success):
- HTTP 200
- Cookie: `JSESSIONID=...`

**Response** (on failure):
- HTTP 401
- No JSESSIONID cookie

**Use Case**: Legacy vManage version support. SDWAN_AI tries this if token-based auth fails.

---

### POST /dataservice/admin/token

Modern authentication endpoint (vManage 20.x+). Returns Bearer token for subsequent requests.

**Method**: POST

**Path**: `/dataservice/admin/token`

**Request**:
```json
{
  "j_username": "admin",
  "j_password": "Cisco123!"
}
```

**Response** (on success, HTTP 200):
```json
{
  "tokenId": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires": 1800
}
```

**Response Headers**:
- Set-Cookie: JSESSIONID=...
- Set-Cookie: X-XSRF-TOKEN=...

**Use Case**: Primary auth method for modern vManage deployments. Token valid for 30 minutes; refresh before expiry.

**Error Handling**:
```python
response = requests.post(
    f"{base_url}/dataservice/admin/token",
    json={"j_username": user, "j_password": password},
    verify=False,
    timeout=30
)
if response.status_code == 401:
    raise VManageAPIError("Invalid credentials")
elif response.status_code != 200:
    raise VManageAPIError(f"Auth failed: {response.status_code}")

token = response.json()["tokenId"]
# Use in subsequent requests
headers = {"Authorization": f"Bearer {token}"}
```

---

## Device Inventory & Management

### GET /dataservice/device

List all devices in the fabric (controllers, edges, etc.).

**Method**: GET

**Path**: `/dataservice/device`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page (default 10, max 10000) |
| `offset` | int | Pagination offset (default 0) |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "deviceId": "0.0.0.0",
      "uuid": "CSR1000V-xxx-uuid",
      "hostname": "hub-1",
      "site-id": "100",
      "device-type": "vsmarts",
      "device-model": "vSmartController",
      "system-ip": "10.1.1.1",
      "organization-name": "Cisco",
      "reachability": "reachable",
      "status": "normal",
      "lastupdated": 1705337425123,
      "uptime-date": 1704650400000
    },
    {
      "deviceId": "192.168.1.1",
      "uuid": "vedge-site5-uuid",
      "hostname": "vedge-site5",
      "site-id": "50",
      "device-type": "vedges",
      "device-model": "vedge-CSR1000V",
      "system-ip": "10.0.50.1",
      "reachability": "reachable",
      "status": "normal",
      "lastupdated": 1705337420000
    }
  ],
  "totalRecords": 147,
  "pageNumber": 1
}
```

**Key Response Fields**:
- `uuid`: Unique device identifier (used in most subsequent calls)
- `system-ip`: Management/loopback IP on SD-WAN fabric
- `device-type`: "controllers" (vSmart/vBond), "vedges", "vmanages"
- `reachability`: "reachable" or "unreachable"
- `status`: "normal", "warning", "critical"

**Pagination**:
```python
# Get all devices (handle pagination)
all_devices = []
offset = 0
while True:
    resp = client.get_devices(limit=100, offset=offset)
    if not resp["data"]:
        break
    all_devices.extend(resp["data"])
    offset += 100
```

**Use Case**: Fabric overview, device inventory, reachability status, device model distribution.

---

### GET /dataservice/system/device/controllers

List all controller devices (vSmart, vBond, vManage).

**Method**: GET

**Path**: `/dataservice/system/device/controllers`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "system-ip": "10.1.1.1",
      "host-name": "hub-1",
      "device-model": "vSmartController",
      "device-type": "vsmarts",
      "site-id": "100",
      "state": "up",
      "uuid": "CSR1000V-xxx"
    }
  ],
  "totalRecords": 2
}
```

**Key Response Fields**:
- `system-ip`: Controller management IP
- `device-model`: vSmartController, vBond, vManageCluster
- `state`: "up" or "down"

**Use Case**: Control plane health check, identify controller outages, verify redundancy.

---

### GET /dataservice/system/device/vedges

List all edge devices (vEdge, ISR4000, etc.).

**Method**: GET

**Path**: `/dataservice/system/device/vedges`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "system-ip": "10.0.50.1",
      "host-name": "vedge-site5",
      "device-model": "vedge-CSR1000V",
      "device-type": "vedges",
      "site-id": "50",
      "state": "up",
      "uuid": "vedge-site5-uuid",
      "last-seen": "2025-01-15T10:20:00Z"
    }
  ],
  "totalRecords": 145
}
```

**Key Response Fields**:
- `system-ip`: Edge management IP
- `device-model`: vedge-CSR1000V, vedge-5000, ISR4461, etc.
- `state`: "up" or "down" (relative to controllers)

**Use Case**: Edge device inventory, onboarding verification, model count for capacity planning.

---

## Device Monitoring & Health

### GET /dataservice/device/{system-ip}/status

Get real-time health status of a specific device.

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/status`

**Example**: `/dataservice/device/10.0.50.1/status`

**Response** (HTTP 200):
```json
{
  "uuid": "vedge-site5-uuid",
  "system-ip": "10.0.50.1",
  "host-name": "vedge-site5",
  "device-model": "vedge-CSR1000V",
  "site-id": "50",
  "reachability": "reachable",
  "status": "normal",
  "uptime": 18574800,
  "cpu-load": 25.5,
  "memory-percent": 62.3,
  "connected-vmanages": 1,
  "personality": "vedge",
  "last-heart-beat": 1705337425000,
  "certificates": {
    "validity": "valid",
    "expiration": 1705423825000
  },
  "system": {
    "kernel-version": "4.4.59",
    "os-version": "19.2.1"
  }
}
```

**Key Response Fields**:
- `reachability`: Is device reachable by vManage?
- `cpu-load`: CPU percentage (0-100)
- `memory-percent`: Memory utilization
- `connected-vmanages`: Number of active vManage connections (redundancy check)
- `certificates.expiration`: Certificate expiry timestamp (epoch ms)
- `system.os-version`: Device OS version

**Use Case**: Device health dashboard, capacity monitoring, certificate expiry tracking, device sync verification.

---

### GET /dataservice/device/{system-ip}/system

Detailed system information (same as above, used interchangeably).

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/system`

**Response**: Same as `/status` endpoint.

---

### GET /dataservice/device/{system-ip}/interface

Get interface statistics for a device.

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/interface`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "ifname": "ge-0/0/0",
      "if-admin-status": "up",
      "if-oper-status": "up",
      "ip-address": "10.0.50.1",
      "rx-bytes": 1234567890,
      "rx-packets": 987654,
      "rx-errors": 0,
      "tx-bytes": 9876543210,
      "tx-packets": 1234567,
      "tx-errors": 0,
      "tx-drops": 5,
      "rx-drops": 2,
      "bandwidth": 1000,
      "mtu": 1500,
      "timestamp": 1705337425000
    }
  ]
}
```

**Key Response Fields**:
- `ifname`: Interface name (ge-0/0/0, eth0, etc.)
- `if-oper-status`: "up" or "down"
- `rx-bytes`, `tx-bytes`: Data transferred
- `rx-errors`, `tx-errors`: Transmission errors
- `tx-drops`: Dropped packets (indicates congestion or QoS)

**Use Case**: Interface health, bandwidth utilization, error tracking, packet loss detection.

---

### GET /dataservice/device/{system-ip}/control/connections

List control plane connections (to vSmart/vBond) from a specific device.

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/control/connections`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "peer-type": "vsmart",
      "peer-system-ip": "10.1.1.1",
      "peer-host-name": "hub-1",
      "state": "up",
      "region": "east",
      "uptime": 86400,
      "latency": 12,
      "drops": 0,
      "errors": 0,
      "connect-time": 1705250400000
    }
  ]
}
```

**Key Response Fields**:
- `peer-type`: "vsmart" or "vbond"
- `state`: "up" or "down"
- `latency`: Control plane latency (ms)
- `uptime`: Connection uptime (seconds)
- `drops`, `errors`: Control plane packet loss/errors

**Use Case**: Control plane health, connection state, latency monitoring, failover status.

---

### GET /dataservice/device/{system-ip}/bfd/sessions

Get BFD (Bidirectional Forwarding Detection) session state for a device.

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/bfd/sessions`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "peer-system-ip": "10.1.1.2",
      "peer-host-name": "hub-2",
      "color": "public",
      "state": "up",
      "uptime": 604800,
      "local-tloc": "10.0.50.1:public",
      "remote-tloc": "10.1.1.2:public",
      "latency": 25,
      "jitter": 3,
      "loss-percent": 0.5,
      "flap-count": 0,
      "last-flap": null,
      "detect-time": 3000,
      "tx-interval": 1000,
      "multiplier": 3,
      "timestamp": 1705337425000
    }
  ]
}
```

**Key Response Fields**:
- `state`: "up" or "down"
- `color`: TLOC color (public, private, metro-ethernet, mpls, 3g, lte, etc.)
- `latency`: One-way latency (ms)
- `loss-percent`: Packet loss percentage
- `flap-count`: Number of state changes (high = unstable link)
- `last-flap`: Timestamp of last state change
- `detect-time`: BFD detection time (how fast to detect failure)

**Use Case**: Data plane health, tunnel stability, jitter/loss detection, flap investigation.

---

### GET /dataservice/device/{system-ip}/omp/peers

Get OMP (Overlay Management Protocol) peer state for a device.

**Method**: GET

**Path**: `/dataservice/device/{system-ip}/omp/peers`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "system-ip": "10.1.1.1",
      "host-name": "hub-1",
      "state": "up",
      "uptime": 1209600,
      "site-id": "100",
      "address-families": ["ipv4"],
      "routes-received": 1500,
      "routes-installed": 1450,
      "tlocs-received": 450,
      "tlocs-installed": 400,
      "eomprime": false,
      "region": "east"
    }
  ]
}
```

**Key Response Fields**:
- `state`: "up" or "down"
- `routes-received` vs `routes-installed`: Indicates route filtering/policy
- `tlocs-received` vs `tlocs-installed`: Transport location availability
- `eomprime`: Extended OMP (if true, peer supports advanced features)

**Use Case**: Control plane routing health, OMP convergence time, route leaking, neighbor state.

---

## Statistics & Performance

### GET /dataservice/statistics/approute

Get application-aware routing statistics (AAR policy enforcement).

**Method**: GET

**Path**: `/dataservice/statistics/approute`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page |
| `timestart` | int | Start epoch (ms) |
| `timeend` | int | End epoch (ms) |
| `device` | string | Filter by device system-ip |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "device": "10.0.50.1",
      "policy-name": "AAR-Cloud-Apps",
      "app-name": "Office365",
      "source-ip": "192.168.1.100",
      "dest-ip": "13.107.4.50",
      "protocol": "tcp",
      "dest-port": 443,
      "packets": 5000,
      "bytes": 2500000,
      "timestamp": 1705337400000,
      "action": "primary-path"
    }
  ]
}
```

**Key Response Fields**:
- `policy-name`: AAR policy that matched
- `app-name`: Detected application
- `action`: "primary-path", "backup-path", "best-path" (which tunnel was used)
- `packets`, `bytes`: Traffic volume

**Use Case**: AAR policy validation, traffic steering verification, application path analysis.

---

### GET /dataservice/statistics/interface

Interface statistics over a time window.

**Method**: GET

**Path**: `/dataservice/statistics/interface`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | string | Device system-ip |
| `interface` | string | Interface name |
| `timestart` | int | Start epoch (ms) |
| `timeend` | int | End epoch (ms) |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "device": "10.0.50.1",
      "interface": "ge-0/0/0",
      "rx-bytes": 1234567890,
      "tx-bytes": 9876543210,
      "rx-packets": 987654,
      "tx-packets": 1234567,
      "rx-errors": 5,
      "tx-errors": 2,
      "rx-drops": 10,
      "tx-drops": 3,
      "timestamp": 1705337400000
    }
  ]
}
```

**Use Case**: Bandwidth trending, error rate analysis, capacity planning.

---

### GET /dataservice/statistics/tunnel

IPsec tunnel statistics.

**Method**: GET

**Path**: `/dataservice/statistics/tunnel`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | string | Source device |
| `remote-system-ip` | string | Remote device |
| `timestart` | int | Start epoch (ms) |
| `timeend` | int | End epoch (ms) |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "device": "10.0.50.1",
      "remote-system-ip": "10.1.1.1",
      "local-color": "public",
      "remote-color": "public",
      "spi": "0x1234abcd",
      "packets": 1000000,
      "bytes": 500000000,
      "drops": 150,
      "rx-duplicates": 5,
      "auth-fail": 0,
      "encrypt-fail": 0,
      "timestamp": 1705337400000
    }
  ]
}
```

**Key Response Fields**:
- `spi`: IPsec Security Parameter Index (tunnel identifier)
- `drops`: Packets dropped (indicates congestion or packet loss)
- `auth-fail`, `encrypt-fail`: Crypto failures (misconfiguration)

**Use Case**: Tunnel health, IPsec error tracking, tunnel capacity analysis.

---

## Alarms & Events

### GET /dataservice/alarms

List active alarms.

**Method**: GET

**Path**: `/dataservice/alarms`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page |
| `offset` | int | Pagination offset |
| `severity` | string | Filter by severity: "Critical", "Major", "Minor", "Warning" |
| `viewed` | bool | Filter by viewed status |
| `cleared` | bool | Include cleared alarms |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "eventname": "OMP Peer Down",
      "eventid": "OMP_PEER_DOWN",
      "system-ip": "10.0.50.1",
      "hostname": "vedge-site5",
      "severity": "Critical",
      "type": "device",
      "message": "OMP peer 10.1.1.1 is down",
      "timestamp": 1705337425000,
      "viewed": false,
      "cleared": false,
      "device-uuid": "vedge-site5-uuid",
      "values": {
        "peer-system-ip": "10.1.1.1"
      }
    }
  ],
  "totalRecords": 23
}
```

**Key Response Fields**:
- `severity`: "Critical", "Major", "Minor", "Warning"
- `eventid`: Machine-readable alarm code
- `message`: Human-readable description
- `values`: Additional context (peer IP, color, etc.)
- `viewed`: Has alarm been acknowledged?

**Use Case**: Alarm triage, severity filtering, incident response.

---

### GET /dataservice/alarms/severity

Get alarm statistics by severity.

**Method**: GET

**Path**: `/dataservice/alarms/severity`

**Response** (HTTP 200):
```json
{
  "Critical": 2,
  "Major": 5,
  "Minor": 12,
  "Warning": 18
}
```

**Use Case**: Fabric health dashboard, SLA compliance tracking.

---

### GET /dataservice/alarms/notviewed

Count of unviewed (unacknowledged) alarms.

**Method**: GET

**Path**: `/dataservice/alarms/notviewed`

**Response** (HTTP 200):
```json
{
  "count": 7
}
```

**Use Case**: Alert on new alarms, notification gateway.

---

### GET /dataservice/event

List system events (template changes, device enrollment, policy updates, etc.).

**Method**: GET

**Path**: `/dataservice/event`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page |
| `offset` | int | Pagination |
| `timestart` | int | Start epoch (ms) |
| `timeend` | int | End epoch (ms) |
| `eventtype` | string | Filter: "template", "policy", "device", "system" |

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "id": "event-uuid-123",
      "eventtype": "template",
      "operation": "attach",
      "details": {
        "template-name": "DC-Site-Template",
        "device-id": "10.0.50.1",
        "status": "success",
        "change-summary": "IP changed 192.168.1.1 -> 10.0.1.1"
      },
      "timestamp": 1705337000000,
      "user": "admin",
      "status": "success"
    }
  ]
}
```

**Key Response Fields**:
- `eventtype`: "template", "policy", "device", "system"
- `operation`: "attach", "detach", "create", "modify", "delete"
- `status`: "success" or "failed"
- `change-summary`: What changed

**Use Case**: Change audit trail, root-cause investigation (what changed before alarm?), rollback planning.

---

## Certificate Management

### GET /dataservice/certificate/list

List all certificates installed on vManage.

**Method**: GET

**Path**: `/dataservice/certificate/list`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "cert-id": "cert-123",
      "cert-name": "SDWAN-Root-CA",
      "cert-type": "root",
      "cert-version": 3,
      "issuer": "CN=SDWAN Root CA, O=Cisco",
      "subject": "CN=SDWAN Root CA, O=Cisco",
      "validity": {
        "not-before": 1672531200000,
        "not-after": 1893456000000
      },
      "fingerprint-sha256": "abcd1234...",
      "installed": true
    }
  ]
}
```

**Key Response Fields**:
- `cert-type`: "root", "device", "intermediate"
- `validity.not-after`: Expiration epoch (ms)
- `installed`: Is this cert active in fabric?

**Use Case**: Certificate inventory, expiry tracking, renewal planning.

---

### GET /dataservice/certificate/vedge/list

List edge device certificates.

**Method**: GET

**Path**: `/dataservice/certificate/vedge/list`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "uuid": "vedge-site5-uuid",
      "hostname": "vedge-site5",
      "system-ip": "10.0.50.1",
      "cert-status": "valid",
      "validity": {
        "not-before": 1672531200000,
        "not-after": 1735689600000
      },
      "days-remaining": 120,
      "certificate": "-----BEGIN CERTIFICATE-----\n..."
    }
  ]
}
```

**Key Response Fields**:
- `cert-status`: "valid", "expired", "revoked"
- `days-remaining`: Days until expiry
- `certificate`: PEM-encoded certificate

**Use Case**: Edge certificate health, enrollment verification, renewal scheduling.

---

### GET /dataservice/certificate/rootcertchain

Get root certificate chain.

**Method**: GET

**Path**: `/dataservice/certificate/rootcertchain`

**Response** (HTTP 200):
```json
{
  "issuer": "CN=SDWAN Root CA, O=Cisco",
  "subject": "CN=SDWAN Root CA, O=Cisco",
  "validity": {
    "not-before": 1672531200000,
    "not-after": 1893456000000
  }
}
```

**Use Case**: Verify root CA, troubleshoot certificate trust issues.

---

## Templates & Policy

### GET /dataservice/template/device

List device templates (chassis, VPN, interface config templates).

**Method**: GET

**Path**: `/dataservice/template/device`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "templateId": "template-uuid-123",
      "templateName": "CSR1000V-Hub",
      "templateType": "cedge",
      "templateDescription": "CSR1000V hub site template",
      "templateVersion": 1,
      "createdBy": "admin",
      "createdOn": 1705000000000,
      "lastModifiedBy": "admin",
      "lastModifiedOn": 1705337000000,
      "templateAttached": true,
      "devicesAttached": 5,
      "generatedBy": "manual"
    }
  ],
  "totalRecords": 42
}
```

**Key Response Fields**:
- `templateId`: Unique template identifier
- `templateType`: "cedge", "vedge", "vsmarts"
- `devicesAttached`: How many devices using this template
- `templateVersion`: Increment on each modification

**Use Case**: Template inventory, attachment graph, version control.

---

### GET /dataservice/template/device/{template-id}

Get detailed template definition (variables, schema).

**Method**: GET

**Path**: `/dataservice/template/device/{template-id}`

**Response** (HTTP 200):
```json
{
  "templateId": "template-uuid-123",
  "templateName": "CSR1000V-Hub",
  "templateType": "cedge",
  "templateDefinition": {
    "generalTemplate": {
      "hostname": "{{hostname}}",
      "system-ip": "{{system-ip}}"
    },
    "vpnTemplate": [
      {
        "vpnId": "0",
        "interfaces": [
          {
            "ifname": "{{lan-interface}}",
            "ip": "{{lan-ip}}/24"
          }
        ]
      }
    ]
  },
  "templateVariables": [
    {
      "name": "hostname",
      "description": "Device hostname",
      "type": "string",
      "value": null
    },
    {
      "name": "system-ip",
      "description": "System IP",
      "type": "ipv4",
      "value": null
    }
  ]
}
```

**Key Response Fields**:
- `templateDefinition`: Actual config template (NETCONF-like structure)
- `templateVariables`: CSV-bindable device-specific values

**Use Case**: Template review, policy impact analysis, variable validation.

---

### GET /dataservice/template/feature

List feature templates (feature-level config modules).

**Method**: GET

**Path**: `/dataservice/template/feature`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "templateId": "feature-uuid-aaa",
      "templateName": "AAA-Config",
      "templateType": "aaa",
      "templateDescription": "RADIUS/TACACS+ authentication",
      "createdBy": "admin",
      "lastModifiedOn": 1705337000000
    }
  ]
}
```

**Use Case**: Feature module reuse, AAA/SNMP/NTP config distribution.

---

### GET /dataservice/template/policy/vsmart

List vSmart centralized policy (control policy + data policy).

**Method**: GET

**Path**: `/dataservice/template/policy/vsmart`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "policyId": "policy-uuid-123",
      "policyName": "QoS-Traffic-Engineering",
      "policyDescription": "Business-critical traffic engineering",
      "policyType": "control",
      "policyDefinition": {
        "assembly": [
          {
            "name": "High-Priority-Apps",
            "definitionId": "def-123",
            "description": "Steer Salesforce to MPLS"
          }
        ]
      },
      "lastModifiedBy": "admin",
      "lastModifiedOn": 1705337000000
    }
  ]
}
```

**Key Response Fields**:
- `policyType`: "control" (traffic engineering) or "data" (flow-based routing)
- `policyDefinition`: Actual policy rules (sequences, matches, actions)

**Use Case**: Policy inventory, policy impact analysis, attachment validation.

---

## Software & Maintenance

### POST /dataservice/device/action/install

Install software image on a device.

**Method**: POST

**Path**: `/dataservice/device/action/install`

**Request Body**:
```json
{
  "action": "install",
  "devices": [
    {
      "deviceId": "10.0.50.1",
      "deviceType": "vedge"
    }
  ],
  "software": "16.12.04"
}
```

**Response** (HTTP 200):
```json
{
  "id": "action-install-123",
  "status": "in_progress",
  "timestamp": 1705337425000
}
```

**Use Case**: Software upgrade orchestration, staged rollout, pre-upgrade validation.

---

### GET /dataservice/software/installed

Get currently installed software versions on all devices.

**Method**: GET

**Path**: `/dataservice/software/installed`

**Response** (HTTP 200):
```json
{
  "data": [
    {
      "device": "10.0.50.1",
      "hostname": "vedge-site5",
      "device-model": "vedge-CSR1000V",
      "installed-version": "16.12.04",
      "available-versions": ["17.03.01", "17.04.02"],
      "timestamp": 1705337425000
    }
  ]
}
```

**Key Response Fields**:
- `installed-version`: Current OS version
- `available-versions`: Upgrade-able versions

**Use Case**: Software inventory, upgrade readiness assessment.

---

### POST /dataservice/system/device/sync

Force vManage to sync configuration to devices.

**Method**: POST

**Path**: `/dataservice/system/device/sync`

**Request Body**:
```json
{
  "devices": ["10.0.50.1", "10.0.51.1"]
}
```

**Response** (HTTP 200):
```json
{
  "syncStatus": "in_progress",
  "devices": [
    {
      "device": "10.0.50.1",
      "status": "syncing"
    }
  ]
}
```

**Use Case**: Force device config sync after template/policy changes, troubleshoot sync delays.

---

## Common Patterns & Best Practices

### Pagination for Large Result Sets

```python
def get_all_resources(endpoint, limit=100):
    """Fetch all results, handling pagination automatically"""
    all_results = []
    offset = 0
    
    while True:
        response = requests.get(
            f"{base_url}{endpoint}",
            params={"limit": limit, "offset": offset},
            headers=auth_headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            break
        
        all_results.extend(data["data"])
        
        if len(data["data"]) < limit:
            break
        
        offset += limit
    
    return all_results
```

### Rate Limiting & Retry

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()

# Retry on transient errors
retry_strategy = Retry(
    total=3,
    backoff_factor=1,  # 1, 2, 4 seconds
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# Rate limiting: max 10 req/sec
max_requests_per_sec = 10
min_interval = 1.0 / max_requests_per_sec

last_request_time = 0
def throttled_get(url):
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    last_request_time = time.time()
    return session.get(url)
```

### Authentication Token Refresh

```python
def ensure_authenticated(client):
    """Re-authenticate if token expired"""
    if client.token_expiry and time.time() >= client.token_expiry:
        logger.info("Token expired, re-authenticating")
        client.authenticate()

def get_with_retry(client, endpoint):
    """GET with automatic re-auth"""
    ensure_authenticated(client)
    return client.get(endpoint)
```

### Response Error Handling

```python
def api_call(method, endpoint, json_body=None):
    """Make API call with comprehensive error handling"""
    try:
        if method == "GET":
            response = session.get(endpoint, timeout=30)
        elif method == "POST":
            response = session.post(endpoint, json=json_body, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling {endpoint}")
        raise VManageAPIError("API timeout (vManage may be overloaded)")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to {endpoint}")
        raise VManageAPIError("Cannot reach vManage (network issue)")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise VManageAPIError("Authentication failed; token expired")
        elif response.status_code == 403:
            raise VManageAPIError("Access denied; check RBAC permissions")
        elif response.status_code == 404:
            raise VManageAPIError(f"Resource not found: {endpoint}")
        elif response.status_code >= 500:
            raise VManageAPIError(f"vManage server error: {response.status_code}")
        else:
            raise VManageAPIError(f"API error: {response.status_code} {response.text}")
```

---

## References

- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
- [REST API Guide (PDF)](https://www.cisco.com/c/en/us/support/docs/routers/software-defined-wan-sdwan/214616-sd-wan-vmanage-rest-api-guide-17-2.html)
- [vManage Release Notes](https://www.cisco.com/c/en/us/support/routers/software-defined-wan-sdwan/series.html)
