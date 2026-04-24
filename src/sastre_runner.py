"""Subprocess wrapper for Sastre CLI operations"""

import logging
import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SastreRunnerError(Exception):
    """Custom exception for Sastre runner errors"""
    pass


class SastreRunner:
    """
    Wrapper for Sastre CLI - executes Sastre commands via subprocess

    Sastre is a configuration management tool for Cisco SD-WAN
    Provides backup, restore, inventory, and template management operations
    """

    def __init__(self, sastre_path: str = "sastre-sd-wan", timeout_sec: int = 60, dryrun_default: bool = True):
        """
        Initialize Sastre runner

        Args:
            sastre_path: Path to sastre-sd-wan executable or command name
            timeout_sec: Timeout for subprocess calls in seconds (default 60)
            dryrun_default: Default dryrun mode for mutating operations (default True for safety)
        """
        self.sastre_path = sastre_path
        self.timeout_sec = timeout_sec
        self.dryrun_default = dryrun_default
        self.env = os.environ.copy()

        # Verify Sastre is available
        try:
            result = subprocess.run(
                [self.sastre_path, "--version"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.returncode == 0:
                logger.info(f"Sastre available: {result.stdout.strip()}")
            else:
                logger.warning(f"Sastre version check returned code {result.returncode}")
        except FileNotFoundError:
            logger.warning(f"Sastre not found at {self.sastre_path} - operations will fail")
        except Exception as e:
            logger.warning(f"Sastre availability check failed: {e}")

    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """
        Execute a command via subprocess and capture output

        Args:
            command: List of command arguments (first element is the executable)

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "returncode": int,
              "command": str
            }
        """
        try:
            logger.debug(f"Running command: {' '.join(command)}")

            result = subprocess.run(
                command,
                capture_output=True,
                timeout=self.timeout_sec,
                text=True,
                env=self.env
            )

            success = result.returncode == 0

            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(command)
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {self.timeout_sec} seconds")
            raise SastreRunnerError(f"Sastre command timed out after {self.timeout_sec} seconds")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise SastreRunnerError(f"Sastre command failed: {e}")

    def list_devices(self) -> Dict[str, Any]:
        """
        List devices known to controller

        Returns:
            {
              "success": bool,
              "devices": [...],
              "device_count": int,
              "stdout": str,
              "stderr": str
            }
        """
        try:
            result = self._run_command([self.sastre_path, "list", "device"])

            # Parse device list from stdout
            devices = []
            for line in result["stdout"].split("\n"):
                line = line.strip()
                if line and not line.startswith("Device"):
                    parts = line.split()
                    if len(parts) >= 2:
                        devices.append({
                            "device_id": parts[0],
                            "hostname": parts[1] if len(parts) > 1 else ""
                        })

            return {
                "success": result["success"],
                "devices": devices,
                "device_count": len(devices),
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return {
                "success": False,
                "devices": [],
                "device_count": 0,
                "error": str(e),
                "command": f"{self.sastre_path} list device"
            }

    def inventory(self) -> Dict[str, Any]:
        """
        Get inventory information (devices, templates, policies)

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "inventory_data": str
            }
        """
        try:
            result = self._run_command([self.sastre_path, "list", "inventory"])

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "inventory_data": result["stdout"],
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Failed to get inventory: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": f"{self.sastre_path} list inventory"
            }

    def backup(self, workdir: str, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Backup device configurations

        Args:
            workdir: Working directory for backup files
            backup_name: Optional backup name/tag

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "backup_path": str
            }
        """
        try:
            # Create workdir if needed
            Path(workdir).mkdir(parents=True, exist_ok=True)

            command = [self.sastre_path, "backup", "--workdir", workdir]
            if backup_name:
                command.extend(["--name", backup_name])

            result = self._run_command(command)

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "backup_path": workdir,
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "backup_path": workdir,
                "command": f"{self.sastre_path} backup --workdir {workdir}"
            }

    def restore(self, workdir: str, dryrun: bool = None) -> Dict[str, Any]:
        """
        Restore device configurations from backup

        Args:
            workdir: Working directory containing backup files
            dryrun: Dry-run mode (default from config, safety-first)

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "dryrun": bool
            }
        """
        if dryrun is None:
            dryrun = self.dryrun_default

        try:
            command = [self.sastre_path, "restore", "--workdir", workdir]
            if dryrun:
                command.append("--dryrun")

            result = self._run_command(command)

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "dryrun": dryrun,
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dryrun": dryrun,
                "command": f"{self.sastre_path} restore --workdir {workdir}"
            }

    def attach_template(self, device_list: List[str] = None, dryrun: bool = None) -> Dict[str, Any]:
        """
        Attach templates to devices

        Args:
            device_list: Optional list of device IDs to filter
            dryrun: Dry-run mode (default from config)

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "dryrun": bool
            }
        """
        if dryrun is None:
            dryrun = self.dryrun_default

        try:
            command = [self.sastre_path, "attach"]
            if dryrun:
                command.append("--dryrun")
            if device_list:
                command.extend(["--devices"] + device_list)

            result = self._run_command(command)

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "dryrun": dryrun,
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Template attach failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dryrun": dryrun,
                "command": f"{self.sastre_path} attach"
            }

    def detach_template(self, device_list: List[str] = None, dryrun: bool = None) -> Dict[str, Any]:
        """
        Detach templates from devices

        Args:
            device_list: Optional list of device IDs to filter
            dryrun: Dry-run mode (default from config)

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str,
              "dryrun": bool
            }
        """
        if dryrun is None:
            dryrun = self.dryrun_default

        try:
            command = [self.sastre_path, "detach"]
            if dryrun:
                command.append("--dryrun")
            if device_list:
                command.extend(["--devices"] + device_list)

            result = self._run_command(command)

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "dryrun": dryrun,
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Template detach failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dryrun": dryrun,
                "command": f"{self.sastre_path} detach"
            }

    def transform(self, config_dir: str = None) -> Dict[str, Any]:
        """
        Transform/normalize configuration data

        Args:
            config_dir: Optional config directory to transform

        Returns:
            {
              "success": bool,
              "stdout": str,
              "stderr": str
            }
        """
        try:
            command = [self.sastre_path, "transform"]
            if config_dir:
                command.extend(["--workdir", config_dir])

            result = self._run_command(command)

            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "command": result["command"]
            }
        except Exception as e:
            logger.error(f"Transform failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": f"{self.sastre_path} transform"
            }
