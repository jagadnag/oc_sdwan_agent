# Deployment Guide for SDWAN_AI

This guide covers setting up SDWAN_AI in local development, lab, and production environments.

---

## Local Development Setup

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git
- Virtual environment (recommended)
- Access to test vManage instance (lab or sandbox)

### Step 1: Clone Repository

```bash
git clone https://github.com/your-company/sdwan-ai.git
cd sdwan-ai
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
./venv/Scripts/Activate.ps1

# Verify
python --version  # Should be 3.9+
pip --version
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt

# Optional: Install dev dependencies (testing, linting)
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment

Create `.env` file in project root:

```bash
# vManage credentials
VMANAGE_HOST=192.168.1.10
VMANAGE_USER=admin
VMANAGE_PASSWORD=Cisco123!
VMANAGE_VERIFY_SSL=false

# Sastre (optional)
VMANAGE_URL=https://192.168.1.10:443

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sdwan_ai.log

# MCP Server
MCP_HOST=localhost
MCP_PORT=7000  # For debugging; OpenCode uses stdio by default
```

### Step 5: Verify vManage Connectivity

```bash
python -c "from src.vmanage_client import VManageClient; \
client = VManageClient(host='192.168.1.10', user='admin', password='Cisco123!', verify_ssl=False); \
client.authenticate(); \
print('Connected to vManage')"

# Output: Connected to vManage
```

### Step 6: Run Local OpenCode Instance

```bash
# Start OpenCode (interactive agent loop)
opencode

# Try a simple command:
# > sdwan-architect: Get fabric overview

# LLM should invoke MCP tools and return results
```

### Step 7: Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_device_tools.py::test_get_devices_success -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## LibreChat MCP Client Setup

LibreChat is a self-hosted ChatGPT alternative that supports MCP for OpenCode integration.

### Step 1: Install LibreChat

```bash
# Clone LibreChat
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat

# Install dependencies
npm install

# Copy env template
cp .env.example .env.local
```

### Step 2: Configure LibreChat for OpenCode

Edit `.env.local`:

```bash
# Enable OpenCode integration
ENABLE_OPENCODE=true

# Point to SDWAN_AI MCP server
MCP_SERVERS=sdwan-tools:file:///path/to/sdwan-ai/src/mcp_server.py

# Enable custom models (Claude API)
OPENAI_API_KEY=sk-...  # Your Anthropic API key
OPENAI_API_BASE=https://api.anthropic.com/openai/

# Model selection
DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

### Step 3: Start LibreChat

```bash
npm start

# Opens at http://localhost:3000
```

### Step 4: Test Connection

1. Navigate to http://localhost:3000
2. Create new conversation
3. Type: "Run morning health check for fabric overview"
4. LibreChat should invoke SDWAN_AI MCP tools via OpenCode
5. Verify tools are being called (check MCP server logs)

---

## Docker Deployment

### Step 1: Create Dockerfile

```dockerfile
# File: Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 sdwan && chown -R sdwan:sdwan /app
USER sdwan

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.vmanage_client import VManageClient; \
    client = VManageClient(host=os.environ['VMANAGE_HOST'], \
    user=os.environ['VMANAGE_USER'], \
    password=os.environ['VMANAGE_PASSWORD']); \
    client.authenticate(); print('healthy')" || exit 1

# Run MCP server
CMD ["python", "src/mcp_server.py"]
```

### Step 2: Create Docker Compose

```yaml
# File: docker-compose.yml

version: '3.8'

services:
  sdwan-ai:
    build: .
    container_name: sdwan-ai-mcp
    environment:
      - VMANAGE_HOST=${VMANAGE_HOST}
      - VMANAGE_USER=${VMANAGE_USER}
      - VMANAGE_PASSWORD=${VMANAGE_PASSWORD}
      - VMANAGE_VERIFY_SSL=${VMANAGE_VERIFY_SSL:-false}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "7000:7000"  # Optional debug port
    volumes:
      - ./logs:/app/logs
      - ./configs:/app/configs
    restart: unless-stopped
    networks:
      - sdwan-network

  librechat:
    image: ghcr.io/danny-avila/librechat:latest
    container_name: librechat
    environment:
      - ENABLE_OPENCODE=true
      - MCP_SERVERS=sdwan-tools:file:///app/sdwan-ai/src/mcp_server.py
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "3000:3000"
    depends_on:
      - sdwan-ai
    volumes:
      - librechat-data:/app/data
    networks:
      - sdwan-network

networks:
  sdwan-network:
    driver: bridge

volumes:
  librechat-data:
```

### Step 3: Deploy

```bash
# Create .env file
cat > .env << EOF
VMANAGE_HOST=192.168.1.10
VMANAGE_USER=admin
VMANAGE_PASSWORD=Cisco123!
VMANAGE_VERIFY_SSL=false
ANTHROPIC_API_KEY=sk-...
EOF

# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f sdwan-ai

# Verify health
docker-compose ps
# Should show both sdwan-ai and librechat as "healthy"
```

---

## Production Hardening

### 1. Credential Management

**Problem**: Storing passwords in .env files is insecure.

**Solution**: Use HashiCorp Vault (or cloud equivalent).

```bash
# Install Vault client
curl https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip | unzip -

# Login to Vault
vault login

# Store vManage credentials
vault kv put secret/sdwan-ai/vmanage \
  host=192.168.1.10 \
  user=admin \
  password=Cisco123!

# Retrieve in Python
import hvac
client = hvac.Client(url='http://vault.company.com:8200')
secret = client.secrets.kv.read_secret_version(path='secret/sdwan-ai/vmanage')
vmanage_host = secret['data']['data']['host']
# etc.
```

### 2. mTLS to vManage

**Problem**: Default HTTPS with `verify_ssl=False` is insecure.

**Solution**: Use certificate-based authentication.

```python
# src/vmanage_client.py

import ssl
import certifi

def __init__(self, ...):
    # Create SSL context
    ssl_context = ssl.create_default_context(
        cafile="/etc/ssl/certs/vmanage-ca.pem"
    )
    ssl_context.load_cert_chain(
        certfile="/etc/ssl/certs/client-cert.pem",
        keyfile="/etc/ssl/private/client-key.pem"
    )
    
    # Use context in requests session
    self.session.verify = ssl_context
```

### 3. Audit Logging

Log all tool invocations for compliance.

```python
# src/audit_logger.py

import json
import logging
from pythonjsonlogger import jsonlogger

# Configure structured JSON logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('/var/log/sdwan-ai/audit.log')
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Log tool invocation
def log_tool_invocation(tool_name: str, user: str, params: dict, result: dict):
    logger.info({
        "event": "tool_invocation",
        "tool": tool_name,
        "user": user,
        "parameters": {k: v for k, v in params.items() if k != 'password'},  # Don't log passwords
        "result_status": result.get("status"),
        "timestamp": datetime.utcnow().isoformat()
    })
```

### 4. RBAC Model

Implement role-based access control for multi-user deployments.

```python
# src/rbac.py

from enum import Enum

class Role(Enum):
    ARCHITECT = "architect"
    OPERATOR = "operator"
    TROUBLESHOOTER = "troubleshooter"
    READONLY = "readonly"

ROLE_PERMISSIONS = {
    Role.ARCHITECT: {
        "get_devices": True,
        "get_alarms": True,
        "validate_policy": True,
        "attach_template": False,  # Ask-before-run
        "attach_policy": False
    },
    Role.OPERATOR: {
        "get_devices": True,
        "attach_template": False,  # Ask-before-run (dryrun first)
        "attach_policy": False
    },
    Role.TROUBLESHOOTER: {
        "get_devices": True,
        "get_alarms": True,
        "get_bfd_sessions": True,
        "attach_template": False
    },
    Role.READONLY: {
        "get_devices": True,
        "get_alarms": True
        # All else: False
    }
}

def check_permission(user: str, role: Role, tool_name: str) -> bool:
    """Verify user has permission to invoke tool"""
    return ROLE_PERMISSIONS[role].get(tool_name, False)
```

### 5. Rate Limiting

Prevent API abuse.

```python
# src/rate_limiter.py

from ratelimit import limits, sleep_and_retry
import time

CALLS_PER_MINUTE = 60

@sleep_and_retry
@limits(calls=CALLS_PER_MINUTE, period=60)
def api_call(endpoint):
    """Rate-limited API call to vManage"""
    # Implementation
    pass
```

### 6. Secrets Rotation

Rotate credentials periodically.

```bash
#!/bin/bash
# rotate-credentials.sh

# Rotate vManage password every 90 days
VMANAGE_HOST=${VMANAGE_HOST}
CURRENT_PASS=$(vault kv get -field=password secret/sdwan-ai/vmanage)

# Set new password on vManage
ssh admin@${VMANAGE_HOST} \
  "request system admin password old-password ${CURRENT_PASS} new-password ${NEW_PASS}"

# Update Vault
vault kv put secret/sdwan-ai/vmanage password=${NEW_PASS}

# Log rotation
echo "Password rotated $(date)" >> /var/log/sdwan-ai/rotation.log
```

---

## Observability & Monitoring

### 1. Structured Logging

Configure JSON logging for analysis in ELK/Splunk.

```python
# src/logging_config.py

import logging
from pythonjsonlogger import jsonlogger

def setup_logging(log_file: str = "logs/sdwan_ai.log"):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # File handler (JSON)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(jsonlogger.JsonFormatter())
    logger.addHandler(file_handler)
    
    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger
```

### 2. Metrics Export

Expose Prometheus metrics.

```python
# src/metrics.py

from prometheus_client import Counter, Histogram, start_http_server
import time

tool_invocations = Counter(
    'sdwan_tool_invocations_total',
    'Total tool invocations',
    ['tool_name', 'status']
)

tool_duration = Histogram(
    'sdwan_tool_duration_seconds',
    'Tool execution time',
    ['tool_name']
)

api_calls = Counter(
    'vmanage_api_calls_total',
    'Total vManage API calls',
    ['endpoint', 'status']
)

@tool
def get_devices():
    start = time.time()
    try:
        result = vmanage_client.get_devices()
        tool_invocations.labels(tool_name='get_devices', status='success').inc()
        tool_duration.labels(tool_name='get_devices').observe(time.time() - start)
        return result
    except Exception as e:
        tool_invocations.labels(tool_name='get_devices', status='error').inc()
        raise

# Expose metrics on :8000/metrics
start_http_server(8000)
```

### 3. Alerting

Set up alerts for critical events.

```yaml
# prometheus-alerts.yml

groups:
  - name: sdwan_ai
    rules:
      - alert: MCP_Server_Down
        expr: up{job="sdwan-ai-mcp"} == 0
        for: 5m
        annotations:
          summary: "SDWAN_AI MCP server is down"
      
      - alert: vManage_Unreachable
        expr: vmanage_api_calls_total{status="error"} > 10
        for: 5m
        annotations:
          summary: "vManage unreachable (10+ failed API calls)"
      
      - alert: Tool_Error_Rate_High
        expr: rate(sdwan_tool_invocations_total{status="error"}[5m]) > 0.1
        for: 10m
        annotations:
          summary: "Tool error rate >10%"
```

---

## Scaling & High Availability

### 1. Distributed MCP Servers

Deploy multiple MCP server instances behind a load balancer.

```yaml
# docker-compose.yml (HA setup)

services:
  sdwan-ai-1:
    build: .
    environment:
      - INSTANCE_ID=1
      - VMANAGE_HOST=${VMANAGE_HOST}
    ports:
      - "7001:7000"
  
  sdwan-ai-2:
    build: .
    environment:
      - INSTANCE_ID=2
      - VMANAGE_HOST=${VMANAGE_HOST}
    ports:
      - "7002:7000"
  
  sdwan-ai-3:
    build: .
    environment:
      - INSTANCE_ID=3
      - VMANAGE_HOST=${VMANAGE_HOST}
    ports:
      - "7003:7000"
  
  nginx-lb:
    image: nginx:latest
    ports:
      - "7000:7000"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - sdwan-ai-1
      - sdwan-ai-2
      - sdwan-ai-3
```

### 2. Caching Strategy

Use Redis for shared cache across instances.

```python
# src/cache.py

import redis

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

def get_devices(use_cache=True):
    cache_key = "devices:all"
    
    if use_cache:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # Fetch from API
    devices = vmanage_client.get_devices()
    
    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(devices))
    
    return devices
```

---

## Troubleshooting Deployment

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution**: Ensure PYTHONPATH is set correctly.

```bash
export PYTHONPATH=/app/sdwan-ai/src:$PYTHONPATH
python src/mcp_server.py
```

### Issue: "Cannot reach vManage"

**Solution**: Verify network connectivity and credentials.

```bash
# Test connectivity
curl -k https://192.168.1.10:443/dataservice/admin/token \
  -d '{"j_username":"admin","j_password":"Cisco123!"}'

# Check firewall
telnet 192.168.1.10 443
```

### Issue: "MCP Server not responding"

**Solution**: Check logs for errors.

```bash
docker logs sdwan-ai-mcp
# Look for Python exceptions or connection errors
```

---

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Prometheus Metrics](https://prometheus.io/docs)
- [Docker Compose](https://docs.docker.com/compose/)
- [Cisco SD-WAN Deployment Guide](https://www.cisco.com/c/en/us/support/docs/routers/software-defined-wan-sdwan/)
