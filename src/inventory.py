"""Controller inventory management from CSV"""

import csv
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ControllerInventory:
    """Manages SD-WAN controller inventory loaded from CSV"""

    def __init__(self, csv_path: str = "controllers.csv"):
        """
        Initialize controller inventory from CSV file

        CSV format:
        name,host,port,role,datacenter,description
        prod-manager,10.10.10.10,443,primary,dc1,Production SD-WAN Manager

        Args:
            csv_path: Path to controllers.csv file
        """
        self.csv_path = csv_path
        self.controllers = {}
        self.load()

    def load(self) -> None:
        """Load controllers from CSV file"""
        if not os.path.exists(self.csv_path):
            logger.warning(f"Controller inventory file not found: {self.csv_path}")
            return

        try:
            with open(self.csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("name"):
                        self.controllers[row["name"]] = {
                            "name": row["name"],
                            "host": row.get("host"),
                            "port": int(row.get("port", 443)),
                            "role": row.get("role"),
                            "datacenter": row.get("datacenter"),
                            "description": row.get("description", ""),
                        }
                logger.info(f"Loaded {len(self.controllers)} controllers from {self.csv_path}")
        except Exception as e:
            logger.error(f"Failed to load controller inventory: {e}")

    def get_controller(self, name: str) -> Optional[Dict]:
        """
        Get controller by name

        Args:
            name: Controller name (e.g., "prod-manager")

        Returns:
            Controller dictionary or None if not found
        """
        return self.controllers.get(name)

    def list_controllers(self) -> List[Dict]:
        """
        Get all controllers

        Returns:
            List of controller dictionaries
        """
        return list(self.controllers.values())

    def get_primary_controller(self) -> Optional[Dict]:
        """
        Get primary controller (role == "primary")

        Returns:
            Primary controller dictionary or None if not found
        """
        for controller in self.controllers.values():
            if controller.get("role") == "primary":
                return controller
        return None

    def get_controllers_by_role(self, role: str) -> List[Dict]:
        """
        Get controllers by role

        Args:
            role: Role name (e.g., "primary", "secondary", "lab")

        Returns:
            List of matching controller dictionaries
        """
        return [c for c in self.controllers.values() if c.get("role") == role]

    def get_controllers_by_datacenter(self, datacenter: str) -> List[Dict]:
        """
        Get controllers in a specific datacenter

        Args:
            datacenter: Datacenter name (e.g., "dc1", "dc2")

        Returns:
            List of matching controller dictionaries
        """
        return [c for c in self.controllers.values() if c.get("datacenter") == datacenter]
