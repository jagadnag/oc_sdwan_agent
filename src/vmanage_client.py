"""vManage REST API Client for Cisco SD-WAN"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class VManageAPIError(Exception):
    """Custom exception for vManage API errors"""
    pass


class VManageClient:
    """
    REST API client for Cisco vManage

    Handles authentication, session management, and API calls to vManage.
    Implements connection pooling, timeout handling, and error recovery.
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = False,
        timeout: int = 30
    ):
        """
        Initialize vManage API client

        Args:
            host: vManage IP or hostname
            user: Administrative username
            password: Administrative password
            port: HTTPS port (default 443)
            verify_ssl: Verify SSL certificates (default False for labs)
            timeout: Request timeout in seconds (default 30)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.base_url = f"https://{self.host}:{self.port}"

        # Session with connection pooling and retry strategy
        self.session = requests.Session()

        # Retry strategy: retry on connection errors, 503, 504
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Disable SSL warnings if verify_ssl is False
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.authenticated = False
        self.token = None
        self.jsessionid = None

        logger.info(f"Initialized vManage client for {self.host}:{self.port}")

    def authenticate(self) -> bool:
        """
        Authenticate to vManage using REST API

        Attempts token-based auth first (20.x+), falls back to JSESSIONID (15.x)

        Returns:
            True if authentication successful

        Raises:
            VManageAPIError if authentication fails
        """
        try:
            logger.info(f"Authenticating to vManage at {self.host}")

            # Attempt token-based authentication (vManage 20.x+)
            auth_url = f"{self.base_url}/dataservice/admin/token"
            response = self.session.post(
                auth_url,
                json={"j_username": self.user, "j_password": self.password},
                verify=self.verify_ssl,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    self.token = data.get("token")
                    if self.token:
                        self.session.headers.update({"X-XSRF-TOKEN": self.token})
                        self.authenticated = True
                        logger.info(f"Successfully authenticated to vManage using token")
                        return True
                except Exception as e:
                    logger.warning(f"Token auth failed, trying legacy auth: {e}")

            # Fall back to JSESSIONID authentication (vManage 15.x-19.x)
            auth_url = f"{self.base_url}/j_security_check"
            response = self.session.post(
                auth_url,
                data={"j_username": self.user, "j_password": self.password},
                verify=self.verify_ssl,
                timeout=self.timeout
            )

            if response.status_code == 200:
                # JSESSIONID should be in cookies
                if "JSESSIONID" in self.session.cookies:
                    self.jsessionid = self.session.cookies["JSESSIONID"]
                    self.authenticated = True
                    logger.info(f"Successfully authenticated to vManage using JSESSIONID")
                    return True

            raise VManageAPIError(f"Authentication failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise VManageAPIError(f"Failed to authenticate: {e}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        HTTP GET request to vManage API

        Args:
            endpoint: API endpoint (e.g., "/dataservice/device")
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            VManageAPIError if request fails
        """
        if not self.authenticated:
            raise VManageAPIError("Not authenticated to vManage")

        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(
                url,
                params=params,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET {endpoint} failed: {e}")
            raise VManageAPIError(f"GET {endpoint} failed: {e}")

    def post(self, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        HTTP POST request to vManage API

        Args:
            endpoint: API endpoint
            json_data: JSON body data

        Returns:
            Parsed JSON response

        Raises:
            VManageAPIError if request fails
        """
        if not self.authenticated:
            raise VManageAPIError("Not authenticated to vManage")

        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(
                url,
                json=json_data,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST {endpoint} failed: {e}")
            raise VManageAPIError(f"POST {endpoint} failed: {e}")

    def put(self, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """HTTP PUT request to vManage API"""
        if not self.authenticated:
            raise VManageAPIError("Not authenticated to vManage")

        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.put(
                url,
                json=json_data,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"PUT {endpoint} failed: {e}")
            raise VManageAPIError(f"PUT {endpoint} failed: {e}")

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """HTTP DELETE request to vManage API"""
        if not self.authenticated:
            raise VManageAPIError("Not authenticated to vManage")

        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.delete(
                url,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except Exception as e:
            logger.error(f"DELETE {endpoint} failed: {e}")
            raise VManageAPIError(f"DELETE {endpoint} failed: {e}")

    def healthcheck(self) -> bool:
        """
        Check vManage API connectivity

        Returns:
            True if API is reachable
        """
        try:
            result = self.get("/dataservice/system/status")
            return result.get("version") is not None
        except Exception as e:
            logger.warning(f"Healthcheck failed: {e}")
            return False

    # Device-specific API calls

    def get_devices(self) -> List[Dict]:
        """
        Get list of all WAN edges

        Returns:
            List of device dictionaries with ID, hostname, model, site-id, etc.
        """
        try:
            result = self.get("/dataservice/device")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []

    def get_device_status(self, device_id: str) -> Dict:
        """Get device reachability status"""
        try:
            return self.get(f"/dataservice/device/status/{device_id}")
        except Exception as e:
            logger.error(f"Failed to get device status for {device_id}: {e}")
            return {}

    def get_device_counters(self, device_id: str) -> Dict:
        """Get device interface counters"""
        try:
            return self.get(f"/dataservice/device/counters/{device_id}")
        except Exception as e:
            logger.error(f"Failed to get device counters for {device_id}: {e}")
            return {}

    def get_control_connections(self) -> List[Dict]:
        """
        Get control plane connections (device to vManage/vSmart)

        Returns:
            List of control connection dictionaries
        """
        try:
            result = self.post(
                "/dataservice/device/control/connections",
                {"query": {}}
            )
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get control connections: {e}")
            return []

    def get_bfd_sessions(self, device_id: str = None) -> List[Dict]:
        """
        Get BFD session status

        Args:
            device_id: Optional device ID to filter

        Returns:
            List of BFD session dictionaries with status, loss, latency, jitter
        """
        try:
            query = {}
            if device_id:
                query = {"__primaryKeyNames": ["device_id", "color", "dst_ip"],
                         "device_id": device_id}
            result = self.post("/dataservice/device/bfd/sessions", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get BFD sessions: {e}")
            return []

    def get_omp_peers(self, device_id: str = None) -> List[Dict]:
        """
        Get OMP peer status

        Returns:
            List of OMP peer dictionaries with peer address, routes received, state
        """
        try:
            query = {}
            if device_id:
                query = {"device_id": device_id}
            result = self.post("/dataservice/device/omp/peers", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get OMP peers: {e}")
            return []

    def get_omp_routes(self, device_id: str = None, vpn: int = None) -> List[Dict]:
        """
        Get OMP routing table (vRoutes, TLOC routes, service routes)

        Args:
            device_id: Optional device ID to filter
            vpn: Optional VPN ID to filter

        Returns:
            List of OMP route dictionaries with prefix, type, attributes
        """
        try:
            query = {}
            if device_id:
                query["device_id"] = device_id
            if vpn is not None:
                query["vpn_id"] = vpn
            result = self.post("/dataservice/device/omp/routes", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get OMP routes: {e}")
            return []

    def get_omp_tlocs(self, device_id: str = None) -> List[Dict]:
        """
        Get TLOC (transport locator) status

        Returns:
            List of TLOC dictionaries with system-ip, color, encapsulation, status
        """
        try:
            query = {}
            if device_id:
                query = {"device_id": device_id}
            result = self.post("/dataservice/device/omp/tlocs", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get OMP TLOCs: {e}")
            return []

    def get_interface_stats(self, device_id: str) -> List[Dict]:
        """Get interface statistics (utilization, errors, drops)"""
        try:
            result = self.post(
                "/dataservice/device/interface/stats",
                {"query": {"device_id": device_id}}
            )
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get interface stats: {e}")
            return []

    def get_alarms(self, query: Dict = None) -> List[Dict]:
        """
        Get alarms with optional filtering

        Args:
            query: Query parameters (e.g., {"severity": "critical"})

        Returns:
            List of alarm dictionaries
        """
        try:
            if query is None:
                query = {}
            result = self.post("/dataservice/alarms", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get alarms: {e}")
            return []

    def get_events(self, query: Dict = None) -> List[Dict]:
        """
        Get events from system event log

        Args:
            query: Query parameters

        Returns:
            List of event dictionaries with timestamp, type, description
        """
        try:
            if query is None:
                query = {}
            result = self.post("/dataservice/event", {"query": query})
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def get_certificates(self) -> List[Dict]:
        """
        Get device certificates (vSmart installed certificates)

        Returns:
            List of certificate dictionaries with CN, validity, expiry
        """
        try:
            result = self.get("/dataservice/certificate/vsmart")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get certificates: {e}")
            return []

    def get_template_list(self) -> List[Dict]:
        """Get list of device templates"""
        try:
            result = self.get("/dataservice/template/device")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get template list: {e}")
            return []

    def get_running_config(self, device_id: str) -> str:
        """
        Get device running configuration

        Args:
            device_id: Device ID

        Returns:
            Running configuration as string
        """
        try:
            result = self.get(f"/dataservice/device/config/running/{device_id}")
            return result.get("running_config", "")
        except Exception as e:
            logger.error(f"Failed to get running config for {device_id}: {e}")
            return ""

    def get_vpn_list(self) -> List[Dict]:
        """Get list of VPNs"""
        try:
            result = self.get("/dataservice/vpn")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get VPN list: {e}")
            return []

    def get_policy_list(self) -> List[Dict]:
        """Get list of centralized policies"""
        try:
            result = self.get("/dataservice/policy")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get policy list: {e}")
            return []

    def get_software_list(self) -> List[Dict]:
        """Get software version list for all devices"""
        try:
            result = self.get("/dataservice/system/software")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get software list: {e}")
            return []
