# SDWAN_AI: Your CCIE Sidekick for Cisco SD-WAN Operations

An AI-powered companion for CCIE-certified Cisco SD-WAN architects managing large-scale enterprise deployments. Powered by Claude Sonnet 4 via OpenCode with specialized agent personas (Architect, Troubleshooter, Operator) and 21 domain-specific skills for design, incident response, and operational excellence.

## 🚀 What It Does

SDWAN_AI augments your expertise with intelligent automation and analysis:

| Use Case | Agent | Benefit | Time Saved |
|----------|-------|---------|------------|
| **Daily Health Checks** | Operator | Comprehensive fabric analysis with risk scoring | 15 min → 2 min |
| **Alarm Triage & RCA** | Troubleshooter | Rapid root cause analysis with correlated metrics | 45 min → 5 min |
| **After-Action Reviews** | Troubleshooter | Systematic incident post-mortems; prevent recurrence | 60 min → 15 min |
| **Upgrade Planning** | Architect | Safe, phased rollout strategies; version compatibility | 6 hours → 2 hours |
| **Site Onboarding** | Architect/Operator | Automated device config generation and staged attachment | 4 hours → 1 hour |
| **Capacity Analysis** | Architect | Device/link/policy utilization trending and forecasts | 3 hours → 30 min |
| **Sastre Workflows** | Operator | Safe backup/restore with dry-run preview and validation | 30 min → 5 min |
| **Template/Policy Updates** | Operator | Controlled multi-stage deployments with health gates | 2 hours → 30 min |
| **Certificate Management** | Operator | Automated expiration tracking and renewal planning | 15 min/day → 2 min/week |
| **Control Plane Issues** | Troubleshooter | vSmart connectivity and OMP peer troubleshooting | 30 min → 10 min |
| **Data Plane Issues** | Troubleshooter | BFD session analysis and tunnel troubleshooting | 45 min → 15 min |

**Result**: 8-12 hours/week reclaimed for strategic work instead of operational repetition.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│                                                                   │
│  (CCIE SD-WAN Architect with 10+ years field experience)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ @sdwan-architect
                           │ @sdwan-troubleshooter  
                           │ @sdwan-operator
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OPENCODE CLIENT                               │
│                                                                   │
│  AI-powered development environment with MCP integration         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CLAUDE SONNET 4                                │
│                                                                   │
│  Orchestrates agent personas, interprets data, generates guides  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              SDWAN_AI AGENTS (3 Personas)                        │
│                                                                   │
│  • Architect    (design, capacity, topology, upgrades)           │
│  • Troubleshooter (RCA, alarms, performance, incidents)          │
│  • Operator     (daily tasks, backups, rollouts, maintenance)    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 21 SPECIALIZED SKILLS                            │
│                                                                   │
│  • daily-health-check    • alarm-correlation                     │
│  • control-plane-issues  • data-plane-issues                     │
│  • certificate-management • backup-restore                       │
│  • capacity-planning     • policy-issues                         │
│  • onboarding-issues     • sdwan-troubleshooting                 │
│  • And 11 more domain-specific skills...                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   ┌──────────────────┐        ┌──────────────────┐
   │ Cisco vManage    │        │  Sastre CLI      │
   │  REST API        │        │ (Backup/Restore) │
   │                  │        │                  │
   │ • Devices        │        │ • Config Export  │
   │ • Alarms         │        │ • Template Mgmt  │
   │ • Statistics     │        │ • Policy Attach  │
   │ • Certificates   │        │ • Transform      │
   │ • Templates      │        │ • Dry-run        │
   │ • Policies       │        │                  │
   └──────────────────┘        └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **OpenCode** (AI-powered development environment)
- **Python 3.10+** with virtual environment
- **Cisco SD-WAN Manager (vManage) 20.x+** with API access
- **Sastre CLI** (optional, but recommended for template management)
- **Network access** to vManage from your workstation

### 1. Clone & Setup Environment

```bash
# Clone repository
git clone https://github.com/your-org/oc_sdwan_agent.git
cd oc_sdwan_agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Sastre (optional, for template workflows)
pip install sastre-pro  # Requires separate Sastre license
```

### 2. Configure vManage Connection

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your vManage credentials
nano .env
```

**Required .env Configuration:**
```bash
# Primary vManage instance (required)
VMANAGE_URL=https://10.10.10.10:8443
VMANAGE_USERNAME=admin
VMANAGE_PASSWORD=your_password_here

# SSL Certificate Verification (set to false for self-signed certs in dev/lab)
VMANAGE_VERIFY_SSL=false

# Sastre Configuration
SASTRE_DATA_DIR=./sastre-data

# Logging Configuration
LOG_LEVEL=INFO
```

### 3. Launch OpenCode

```bash
# Start OpenCode in the project directory
opencode

# The agents will be automatically available via @agent syntax
```

### 4. Test Your Setup

Once OpenCode is running, test the connection:

```
@sdwan-operator run daily health check
```

This will validate your vManage connection and provide a comprehensive fabric health report.

## 🎯 Agent Usage Guide

### Agent Delegation Syntax

Use the `@agent-name` syntax to delegate tasks to specific agents:

```bash
# Strategic planning and design
@sdwan-architect "Plan upgrade path for 500 devices to 20.13"

# Incident response and troubleshooting  
@sdwan-troubleshooter "Analyze BFD flapping on site-101"

# Daily operations and maintenance
@sdwan-operator "Run morning health check and backup configs"
```

### When to Use Each Agent

**🏗️ Architect Agent** - Use for:
- Site onboarding planning
- Capacity analysis and forecasting
- Upgrade path planning
- Topology design recommendations
- Policy strategy development
- Architecture reviews

**🔧 Troubleshooter Agent** - Use for:
- Active incident response
- Root cause analysis
- Alarm correlation and triage
- Performance degradation analysis
- After-action reviews
- Control/data plane issues

**⚙️ Operator Agent** - Use for:
- Daily health checks
- Routine maintenance tasks
- Configuration backups
- Certificate management
- Template/policy rollouts
- Scheduled operations

## 🛠️ Specialized Skills (21 Available)

The agents leverage 21 domain-specific skills for expert-level analysis:

### Core Operations
- **daily-health-check**: Comprehensive fabric monitoring and reporting
- **backup-restore**: Configuration management and disaster recovery
- **certificate-management**: PKI lifecycle and renewal automation

### Troubleshooting & Analysis
- **alarm-correlation**: Event analysis and root cause identification
- **control-plane-issues**: vSmart and control connectivity troubleshooting
- **data-plane-issues**: Tunnel and forwarding troubleshooting
- **policy-issues**: Policy enforcement and routing troubleshooting
- **onboarding-issues**: New device provisioning troubleshooting

### Architecture & Planning
- **capacity-planning**: Growth projections and resource optimization
- **centralized-control-policy**: vSmart routing and path optimization
- **centralized-data-policy**: Security and QoS enforcement
- **localized-policy**: Edge-based policy enforcement

### Security & Compliance
- **zbfw**: Zone-Based Firewall policies
- **url-filtering**: Web content security and access control
- **ips-ids**: Intrusion prevention and detection
- **segmentation**: Microsegmentation and isolation

### Platform Components
- **control-plane**: vSmart policy distribution and optimization
- **data-plane**: vEdge/cEdge packet forwarding and tunnels
- **management-plane**: vManage monitoring and configuration
- **orchestration-plane**: vManage and vBond management functions

### General Methodology
- **sdwan-troubleshooting**: General troubleshooting methodology and tools

## 📋 Real-World Use Cases

### Daily Operations

**Morning Health Check**
```
@sdwan-operator run daily health check
```
**Output**: Comprehensive report with device status, alarm analysis, certificate expiration, risk scoring, and prioritized action items.

**Certificate Management**
```
@sdwan-operator check certificate expiration status
```
**Output**: Certificate inventory with expiration dates, renewal recommendations, and automated tracking.

### Incident Response

**Alarm Triage**
```
@sdwan-troubleshooter analyze critical alarms from last 4 hours
```
**Output**: Correlated alarm analysis, root cause hypotheses, and remediation steps.

**Control Plane Issues**
```
@sdwan-troubleshooter investigate OMP peer flapping on site-205
```
**Output**: Control connection analysis, BFD session status, and connectivity troubleshooting.

### Strategic Planning

**Site Onboarding**
```
@sdwan-architect plan onboarding for 25 new retail sites in APAC region
```
**Output**: Template strategy, capacity analysis, rollout phases, and resource requirements.

**Upgrade Planning**
```
@sdwan-architect design upgrade path from 20.9 to 20.13 for production fabric
```
**Output**: Version compatibility matrix, phased rollout plan, risk assessment, and rollback strategy.

## 🔧 Advanced Features

### Sastre Integration

All configuration changes use Sastre CLI with safety features:

```bash
# Agents automatically use dry-run first
sastre attach device-group --template-group new-branch --dry-run

# Show diffs before execution
sastre show template branch-template-v2

# Safe backup before changes
sastre backup --workdir ./sastre-data
```

### Health Check Report Generation

**Automated Report Generation:**
```bash
# Generate comprehensive health report
python src/generate_health_report.py --project-dir . --output-dir reports --alarm-days 1
```

**Output**: Markdown report with AI-generated executive summary, technical analysis, and recommendations.

### Multi-Controller Support

Configure multiple vManage instances in `controllers.csv`:
```csv
name,host,port,role,datacenter,description
prod-manager,10.10.10.10,443,primary,dc1,Production SD-WAN Manager - Primary
dr-manager,10.10.20.10,443,secondary,dc2,Production SD-WAN Manager - DR
lab-manager,192.168.1.10,443,lab,lab,Lab SD-WAN Manager for Testing
```

## 📊 Feature Matrix

| Feature | Architect | Troubleshooter | Operator | Status |
|---------|-----------|-----------------|----------|--------|
| Device Inventory & Topology | ✅ | ✅ | ✅ | Production |
| Health Summaries (real-time) | ✅ | ✅ | ✅ | Production |
| Alarm Triage & Correlation | ✅ | ✅ | ✅ | Production |
| Root Cause Analysis | — | ✅ | — | Production |
| After-Action Reviews | — | ✅ | — | Production |
| Capacity Planning & Trends | ✅ | — | — | Production |
| Template Design & Recommendations | ✅ | — | ✅ | Production |
| Policy Design & Review | ✅ | — | ✅ | Production |
| Upgrade Path Planning | ✅ | — | — | Production |
| Sastre Backup/Restore | — | — | ✅ | Production |
| Template Attachment (staged) | ✅ | — | ✅ | Production |
| Policy Activation (staged) | ✅ | — | ✅ | Production |
| Site Onboarding Workflows | ✅ | — | ✅ | Production |
| Certificate Management | — | — | ✅ | Production |
| Risk Scoring & Assessment | ✅ | ✅ | ✅ | Production |
| BFD Session Analysis | — | ✅ | ✅ | Production |
| Control Plane Monitoring | — | ✅ | ✅ | Production |
| Performance Metrics Analysis | ✅ | ✅ | ✅ | Production |
| ThousandEyes Correlation | — | ✅ | — | Phase 2 |
| Catalyst Center Integration | ✅ | — | — | Phase 2 |
| Multi-Vendor Support | — | — | — | Phase 3 |

## 🔍 Cisco SD-WAN API Endpoints

The agents query and interact with these vManage REST API endpoints:

### Device Management
- `/dataservice/device` — Device inventory, status, connectivity
- `/dataservice/device/config` — Device-level configurations  
- `/dataservice/system/device/info` — Hardware/OS information
- `/dataservice/system/device/versions` — Software versions

### Health & Monitoring
- `/dataservice/alarms` — Active alarms with severity and timestamps
- `/dataservice/system/stats` — System-wide health metrics
- `/dataservice/device/statistics` — Per-device CPU, memory, throughput
- `/dataservice/network/connectivity` — Site-to-site reachability
- `/dataservice/device/interface` — Interface statistics

### Control & Data Plane
- `/dataservice/device/omp/peers` — OMP neighbor status
- `/dataservice/device/bfd/sessions` — BFD session status
- `/dataservice/device/control/connections` — Control connections
- `/dataservice/network/topology` — Network topology graph

### Security & Certificates
- `/dataservice/certificate/management/devices` — Certificate status
- `/dataservice/certificate/management/csr` — Certificate requests

### Configuration Management
- `/dataservice/template/device/config` — Device templates
- `/dataservice/template/policy/list` — Available policies
- `/dataservice/audit` — Configuration audit trail

## 🛡️ Security & Safety

### Credential Management
- All credentials stored in `.env` (never committed to git)
- SSL certificate validation configurable
- Role-based access control through vManage

### Change Safety
- **Read-only by default**: Agents query before recommending changes
- **Explicit approval required**: All modifications require human confirmation
- **Dry-run preview**: Sastre shows diffs before live execution
- **Automatic backups**: Snapshots created before major changes
- **Audit trail**: All actions logged with timestamps

### Permission Model
- `edit`: denied (prevents unintended file modifications)
- `bash`: ask (requires approval for Sastre/system commands)
- `webfetch`: denied (prevents external data leakage)

## 🗂️ Project Structure

```
oc_sdwan_agent/
├── README.md                          # This comprehensive guide
├── AGENTS.md                          # Core agent instructions
├── .env.example                       # Environment template
├── requirements.txt                   # Python dependencies
├── controllers.csv                    # vManage instance catalog
│
├── src/                               # Core Python package
│   ├── generate_health_report.py     # Automated health reporting
│   ├── report_generator.py           # Report generation engine
│   ├── vmanage_client.py             # vManage REST API client
│   ├── collector.py                  # Data collection from vManage
│   ├── sastre_runner.py              # Sastre CLI integration
│   │
│   ├── analyzers/                    # Analysis modules
│   │   ├── alarm_correlator.py       # Alarm correlation engine
│   │   ├── bfd_analyzer.py           # BFD session analysis
│   │   ├── control_analyzer.py       # Control plane analysis
│   │   ├── risk_scorer.py            # Risk assessment engine
│   │   └── legacy_analyzer.py        # Legacy system analysis
│   │
│   ├── workflows/                    # Operational workflows
│   │   ├── morning_health_check.py   # Daily health check workflow
│   │   ├── incident_triage.py        # Incident response workflow
│   │   ├── site_onboarder.py         # Site onboarding automation
│   │   ├── upgrade_planner.py        # Upgrade planning workflow
│   │   └── change_validator.py       # Change validation workflow
│   │
│   └── tools/                        # Tool implementations
│       ├── inventory_tools.py        # Device inventory tools
│       ├── alarm_tools.py            # Alarm management tools
│       ├── certificate_tools.py      # Certificate management
│       ├── control_plane_tools.py    # Control plane tools
│       ├── data_plane_tools.py       # Data plane tools
│       ├── policy_tools.py           # Policy management tools
│       ├── sastre_tools.py           # Sastre integration tools
│       └── upgrade_tools.py          # Upgrade management tools
│
├── .opencode/                        # OpenCode configuration
│   └── skills/                       # 21 specialized skills
│       ├── daily-health-check/       # Daily operations skill
│       ├── alarm-correlation/        # Alarm analysis skill
│       ├── control-plane-issues/     # Control troubleshooting
│       ├── data-plane-issues/        # Data plane troubleshooting
│       ├── certificate-management/   # Certificate lifecycle
│       ├── backup-restore/           # Configuration management
│       ├── capacity-planning/        # Growth analysis
│       ├── onboarding-issues/        # Device provisioning
│       ├── policy-issues/            # Policy troubleshooting
│       ├── sdwan-troubleshooting/    # General methodology
│       └── ... (11 more skills)
│
├── docs/                             # Documentation
│   ├── API.md                        # vManage API reference
│   ├── SASTRE_REFERENCE.md           # Sastre CLI guide
│   ├── SECURITY.md                   # Security guidelines
│   └── EXAMPLES.md                   # Usage examples
│
├── examples/                         # Example workflows
│   ├── daily_health_check.md
│   ├── incident_response.md
│   ├── site_onboarding.md
│   └── upgrade_planning.md
│
└── tests/                            # Test suite
    ├── test_vmanage_client.py
    ├── test_analyzers.py
    └── test_workflows.py
```

## 🚧 Troubleshooting

### Common Setup Issues

**1. vManage Connection Failed**
```bash
# Check network connectivity
ping your-vmanage-ip

# Verify credentials in .env
cat .env | grep VMANAGE

# Test API access
curl -k https://your-vmanage-ip:8443/dataservice/device
```

**2. Sastre Not Found**
```bash
# Install Sastre
pip install sastre-pro

# Verify installation
sastre --version

# Check PATH
which sastre
```

**3. SSL Certificate Issues**
```bash
# For lab environments, disable SSL verification
echo "VMANAGE_VERIFY_SSL=false" >> .env

# For production, add CA certificate path
echo "VMANAGE_CA_CERT=/path/to/ca-bundle.crt" >> .env
```

**4. Permission Denied**
```bash
# Ensure proper file permissions
chmod 600 .env

# Check Python virtual environment
which python
pip list | grep -E "(requests|aiohttp)"
```

### Getting Help

**Agent Not Responding**
- Verify OpenCode is running in the project directory
- Check that .env file is properly configured
- Try a simple test: `@sdwan-operator check connection`

**Health Check Fails**
- Ensure vManage is reachable and credentials are correct
- Check that your user has read permissions on vManage
- Verify API is enabled on vManage (Administration > Settings > API)

**Sastre Operations Fail**
- Ensure Sastre is installed and licensed
- Check that SASTRE_DATA_DIR exists and is writable
- Verify vManage credentials work with Sastre CLI directly

## 🗺️ Roadmap

### Current (Production Ready)
✅ Three specialized agent personas  
✅ 21 domain-specific skills  
✅ Comprehensive health checking  
✅ Sastre CLI integration  
✅ Real-time alarm correlation  
✅ Certificate management  
✅ Risk assessment and scoring  
✅ OpenCode integration  

### Phase 2 (Q2 2026)
🔄 ThousandEyes integration for app performance correlation  
🔄 Catalyst Center integration for multi-vendor policy  
🔄 Advanced ML-based capacity forecasting  
🔄 HTML/PDF reporting with dashboards  
🔄 Slack/Teams notifications  

### Phase 3 (Q3 2026)
📋 Multi-vendor SD-WAN support (Meraki, Arista, Juniper)  
📋 Comparative architecture recommendations  
📋 Automated policy synthesis from business intent  
📋 ServiceNow/Jira integration for change management  

## 📄 License

Apache License 2.0. See [LICENSE](./LICENSE) for details.

## 🤝 Support & Contributing

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: See [docs/](./docs/) and [examples/](./examples/)
- **Development**: See [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Community**: Join our discussions for best practices and use cases

---

**SDWAN_AI**: Because every SD-WAN architect deserves a 24/7 CCIE-grade sidekick. 🚀

*Transform your SD-WAN operations from reactive firefighting to proactive excellence.*
