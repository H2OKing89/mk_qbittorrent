"""
Settings Storage Manager
Handles multi-layered configuration storage for UI frontend
"""
import json
import asyncio
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import asdict
import logging

from ..core.config_manager import ConfigManager, AppConfig
from ..utils.credential_manager import CredentialManager

logger = logging.getLogger(__name__)

class SettingsStorageManager:
    """
    Multi-layered settings storage for UI frontends
    
    Layers (in priority order):
    1. Runtime Settings - Temporary, in-memory changes
    2. User Settings - Persistent user customizations
    3. Base Config - config.yaml (read-only for UI)
    4. Defaults - Hardcoded application defaults
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.config_manager = ConfigManager()
        self.credential_manager = CredentialManager()
        
        # Storage paths
        self.user_settings_file = Path(f"config/user_settings_{user_id}.json")
        self.runtime_settings_file = Path(f"config/runtime_settings_{user_id}.json")
        
        # In-memory caches
        self._runtime_settings: Dict[str, Any] = {}
        self._user_settings: Dict[str, Any] = {}
        
        # Load existing settings
        self._load_user_settings()
        self._load_runtime_settings()
    
    def get_effective_settings(self) -> Dict[str, Any]:
        """
        Get the effective settings by merging all layers
        Priority: Runtime > User > Base Config > Defaults
        """
        try:
            # Start with base config
            base_config = self.config_manager.get_config()
            effective = base_config.to_dict()
            
            # Apply user customizations
            effective = self._merge_settings(effective, self._user_settings)
            
            # Apply runtime changes
            effective = self._merge_settings(effective, self._runtime_settings)
            
            return effective
            
        except Exception as e:
            logger.error(f"Error getting effective settings: {e}")
            return {}
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get a specific settings section with all layers applied"""
        effective = self.get_effective_settings()
        return effective.get(section, {})
    
    def update_setting(self, section: str, key: str, value: Any, 
                      layer: str = "user", persist: bool = True) -> bool:
        """
        Update a specific setting
        
        Args:
            section: Settings section (e.g., 'qbittorrent', 'torrent_creation')
            key: Setting key within the section
            value: New value
            layer: Storage layer ('runtime' or 'user')
            persist: Whether to save to disk
            
        Returns:
            True if successful
        """
        try:
            if layer == "runtime":
                self._update_runtime_setting(section, key, value)
                if persist:
                    self._save_runtime_settings()
            elif layer == "user":
                self._update_user_setting(section, key, value)
                if persist:
                    self._save_user_settings()
            else:
                raise ValueError(f"Unknown layer: {layer}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating setting {section}.{key}: {e}")
            return False
    
    def update_section(self, section: str, settings: Dict[str, Any], 
                      layer: str = "user", persist: bool = True) -> bool:
        """Update an entire settings section"""
        try:
            for key, value in settings.items():
                self.update_setting(section, key, value, layer, persist=False)
            
            if persist:
                if layer == "runtime":
                    self._save_runtime_settings()
                elif layer == "user":
                    self._save_user_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating section {section}: {e}")
            return False
    
    def reset_setting(self, section: str, key: str, layer: str = "user") -> bool:
        """Reset a setting to its base config value"""
        try:
            if layer == "runtime":
                if section in self._runtime_settings and key in self._runtime_settings[section]:
                    del self._runtime_settings[section][key]
                    self._save_runtime_settings()
            elif layer == "user":
                if section in self._user_settings and key in self._user_settings[section]:
                    del self._user_settings[section][key]
                    self._save_user_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting setting {section}.{key}: {e}")
            return False
    
    def reset_section(self, section: str, layer: str = "user") -> bool:
        """Reset an entire section to base config values"""
        try:
            if layer == "runtime":
                if section in self._runtime_settings:
                    del self._runtime_settings[section]
                    self._save_runtime_settings()
            elif layer == "user":
                if section in self._user_settings:
                    del self._user_settings[section]
                    self._save_user_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting section {section}: {e}")
            return False
    
    def reset_all(self, layer: str = "user") -> bool:
        """Reset all settings in a layer"""
        try:
            if layer == "runtime":
                self._runtime_settings = {}
                self._save_runtime_settings()
            elif layer == "user":
                self._user_settings = {}
                self._save_user_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting all settings in layer {layer}: {e}")
            return False
    
    def get_layer_info(self) -> Dict[str, Any]:
        """Get information about each settings layer"""
        base_config = self.config_manager.get_config()
        
        return {
            "base_config": {
                "source": str(self.config_manager.config_path),
                "sections": list(base_config.to_dict().keys()),
                "read_only": True
            },
            "user_settings": {
                "source": str(self.user_settings_file),
                "sections": list(self._user_settings.keys()),
                "count": sum(len(section.keys()) if isinstance(section, dict) else 1 
                           for section in self._user_settings.values())
            },
            "runtime_settings": {
                "source": str(self.runtime_settings_file),
                "sections": list(self._runtime_settings.keys()),
                "count": sum(len(section.keys()) if isinstance(section, dict) else 1 
                           for section in self._runtime_settings.values()),
                "temporary": True
            }
        }
    
    def apply_to_base_config(self, section: Optional[str] = None) -> bool:
        """
        Apply user settings to base config file (permanent change)
        Use with caution - this modifies config.yaml
        """
        try:
            if section:
                # Apply specific section
                if section in self._user_settings:
                    base_config = self.config_manager.get_config()
                    section_settings = self._user_settings[section]
                    
                    if hasattr(base_config, section):
                        section_obj = getattr(base_config, section)
                        for key, value in section_settings.items():
                            if hasattr(section_obj, key):
                                setattr(section_obj, key, value)
                    
                    self.config_manager.save_config()
                    
                    # Remove from user settings since it's now in base config
                    del self._user_settings[section]
                    self._save_user_settings()
            else:
                # Apply all user settings
                base_config = self.config_manager.get_config()
                effective = self._merge_settings(base_config.to_dict(), self._user_settings)
                
                new_config = AppConfig.from_dict(effective)
                self.config_manager.config = new_config
                self.config_manager.save_config()
                
                # Clear user settings
                self._user_settings = {}
                self._save_user_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying to base config: {e}")
            return False
    
    # Private methods
    
    def _update_runtime_setting(self, section: str, key: str, value: Any):
        """Update a runtime setting"""
        if section not in self._runtime_settings:
            self._runtime_settings[section] = {}
        self._runtime_settings[section][key] = value
    
    def _update_user_setting(self, section: str, key: str, value: Any):
        """Update a user setting"""
        if section not in self._user_settings:
            self._user_settings[section] = {}
        self._user_settings[section][key] = value
    
    def _merge_settings(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge settings dictionaries"""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _load_user_settings(self):
        """Load user settings from file"""
        try:
            if self.user_settings_file.exists():
                with open(self.user_settings_file, 'r') as f:
                    self._user_settings = json.load(f)
            else:
                self._user_settings = {}
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
            self._user_settings = {}
    
    def _load_runtime_settings(self):
        """Load runtime settings from file"""
        try:
            if self.runtime_settings_file.exists():
                with open(self.runtime_settings_file, 'r') as f:
                    self._runtime_settings = json.load(f)
            else:
                self._runtime_settings = {}
        except Exception as e:
            logger.error(f"Error loading runtime settings: {e}")
            self._runtime_settings = {}
    
    def _save_user_settings(self):
        """Save user settings to file"""
        try:
            self.user_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_settings_file, 'w') as f:
                json.dump(self._user_settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
    
    def _save_runtime_settings(self):
        """Save runtime settings to file"""
        try:
            self.runtime_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.runtime_settings_file, 'w') as f:
                json.dump(self._runtime_settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving runtime settings: {e}")


class SettingsValidator:
    """Validates settings before applying them"""
    
    @staticmethod
    def validate_qbittorrent_settings(settings: Dict[str, Any]) -> tuple[bool, str]:
        """Validate qBittorrent settings"""
        try:
            if 'host' in settings and not settings['host']:
                return False, "Host cannot be empty"
            
            if 'port' in settings:
                port = settings['port']
                if not isinstance(port, int) or not (1 <= port <= 65535):
                    return False, f"Invalid port: {port}"
            
            if 'connection_timeout' in settings:
                timeout = settings['connection_timeout']
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    return False, f"Invalid connection timeout: {timeout}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    @staticmethod
    def validate_torrent_creation_settings(settings: Dict[str, Any]) -> tuple[bool, str]:
        """Validate torrent creation settings"""
        try:
            if 'format' in settings:
                valid_formats = ['v1', 'v2', 'hybrid']
                if settings['format'] not in valid_formats:
                    return False, f"Invalid format. Must be one of: {valid_formats}"
            
            if 'piece_size' in settings and settings['piece_size'] is not None:
                piece_size = settings['piece_size']
                if not isinstance(piece_size, int) or piece_size < 0:
                    return False, f"Invalid piece size: {piece_size}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    @staticmethod
    def validate_web_server_settings(settings: Dict[str, Any]) -> tuple[bool, str]:
        """Validate web server settings"""
        try:
            if 'port' in settings:
                port = settings['port']
                if not isinstance(port, int) or not (1024 <= port <= 65535):
                    return False, f"Invalid port: {port}. Use 1024-65535"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    @classmethod
    def validate_section(cls, section: str, settings: Dict[str, Any]) -> tuple[bool, str]:
        """Validate settings for a specific section"""
        validators = {
            'qbittorrent': cls.validate_qbittorrent_settings,
            'torrent_creation': cls.validate_torrent_creation_settings,
            'web_server': cls.validate_web_server_settings
        }
        
        validator = validators.get(section)
        if validator:
            return validator(settings)
        else:
            return True, "No validation rules for this section"
