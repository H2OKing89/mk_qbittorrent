"""
Configuration Manager
Handles loading, validation, and management of application configuration
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import yaml
except ImportError:
    yaml = None


class TorrentFormat(Enum):
    """Supported torrent formats"""
    V1 = "v1"
    V2 = "v2"
    HYBRID = "hybrid"


@dataclass
class QBittorrentConfig:
    """qBittorrent connection and behavior configuration"""
    host: str = "localhost"
    port: int = 8080
    username: str = "admin"
    password: str = "adminpass"
    
    # New auth structure
    auth_mode: str = "secret"  # 'secret' | 'plain'
    username_ref: str = "QBIT_USERNAME"
    password_ref: str = "QBIT_PASSWORD"
    use_https: bool = False
    base_path: str = ""
    verify_tls: bool = True
    auth: Optional[Dict[str, Any]] = None
    
    # Connection timeouts and performance (aligned with documentation best practices)
    connection_timeout: float = 10.0  # Connect timeout in seconds
    read_timeout: float = 30.0        # Read timeout in seconds
    pool_connections: int = 10        # HTTP connection pool size
    pool_maxsize: int = 10           # HTTP connection pool max size
    
    # qBittorrent behavior
    category: str = "torrents"
    save_path: str = "/downloads"
    auto_add_after_creation: bool = True
    auto_torrent_management: bool = False
    tags: Optional[List[str]] = None
    trackers: Optional[List[str]] = None
    docker_path_mapping: Optional[Dict[str, str]] = None
    max_tag_length: int = 50
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.trackers is None:
            self.trackers = []
        if self.docker_path_mapping is None:
            self.docker_path_mapping = {}


@dataclass 
class TorrentCreationConfig:
    """Torrent creation specific configuration"""
    format: str = "v2"
    private: bool = True
    start_seeding: bool = False
    comment: str = "Created with Easy Torrent Creator"
    piece_size: Optional[int] = None
    optimize_alignment: bool = True
    padded_file_size_limit: Optional[int] = None
    timeout: int = 300
    poll_interval: float = 1.0
    url_seeds: Optional[List[str]] = None  # Web seeds / HTTP seeds
    source: str = ""  # Content source/description
    
    def __post_init__(self):
        if self.url_seeds is None:
            self.url_seeds = []


@dataclass
class WebServerConfig:
    """Web server configuration"""
    host: str = "0.0.0.0"
    port: int = 8094
    reload: bool = True


@dataclass
class DebugConfig:
    """Debug and logging configuration"""
    log_level: str = "INFO"
    api_debug: bool = False
    metrics: bool = False


@dataclass
class AppConfig:
    """Main application configuration"""
    qbittorrent: QBittorrentConfig
    torrent_creation: TorrentCreationConfig
    web_server: WebServerConfig
    default_output_dir: str = "./torrents"
    default_upload_root: str = "/mnt/user/data"
    remember_last_folder: bool = True
    auto_open_output_folder: bool = True
    docker_mapping: Optional[Dict[str, Any]] = None
    debug: Optional[DebugConfig] = None
    
    def __post_init__(self):
        if self.debug is None:
            self.debug = DebugConfig()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create AppConfig from dictionary"""
        qbit_data = data.get('qbittorrent', {})
        creation_data = data.get('torrent_creation', {})
        web_server_data = data.get('web_server', {})
        docker_mapping_data = data.get('docker_mapping', {})
        debug_data = data.get('debug', {})
        
        return cls(
            qbittorrent=QBittorrentConfig(**qbit_data),
            torrent_creation=TorrentCreationConfig(**creation_data),
            web_server=WebServerConfig(**web_server_data),
            default_output_dir=data.get('default_output_dir', './torrents'),
            default_upload_root=data.get('default_upload_root', '/mnt/user/data'),
            remember_last_folder=data.get('remember_last_folder', True),
            auto_open_output_folder=data.get('auto_open_output_folder', True),
            docker_mapping=docker_mapping_data if docker_mapping_data else None,
            debug=DebugConfig(**debug_data) if debug_data else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AppConfig to dictionary"""
        result = {
            'qbittorrent': asdict(self.qbittorrent),
            'torrent_creation': asdict(self.torrent_creation),
            'web_server': asdict(self.web_server),
            'default_output_dir': self.default_output_dir,
            'default_upload_root': self.default_upload_root,
            'remember_last_folder': self.remember_last_folder,
            'auto_open_output_folder': self.auto_open_output_folder
        }
        
        if self.docker_mapping:
            result['docker_mapping'] = self.docker_mapping
            
        if self.debug:
            result['debug'] = asdict(self.debug)
            
        return result


class ConfigManager:
    """Manages application configuration loading, saving, and validation"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[AppConfig] = None
        self._last_folder_file = Path("config/.last_folder")
        
    def load_config(self) -> AppConfig:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            if yaml is None:
                raise ConfigError("PyYAML is required but not installed. Please install with: pip install PyYAML")
            try:
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                self.config = AppConfig.from_dict(data)
                return self.config
            except Exception as e:
                raise ConfigError(f"Failed to load config from {self.config_path}: {e}")
        else:
            # Create default configuration
            self.config = self._create_default_config()
            self.save_config()
            return self.config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        if not self.config:
            raise ConfigError("No configuration to save")
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        if yaml is None:
            raise ConfigError("PyYAML is required but not installed. Please install with: pip install PyYAML")
        
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config.to_dict(), f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigError(f"Failed to save config to {self.config_path}: {e}")
    
    def get_config(self) -> AppConfig:
        """Get current configuration, loading if necessary"""
        if not self.config:
            return self.load_config()
        return self.config
    
    def _resolve_env_vars(self, value):
        """Resolve environment variables and secure credentials in configuration values"""
        if not isinstance(value, str):
            return value
        
        if '${' not in value:
            return value
        
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            
            # Try to get from secure credential manager if available
            try:
                from ..utils.credential_manager import CredentialManager
                credential_manager = CredentialManager()
                secure_value = credential_manager.get_credential(var_name)
                if secure_value is not None:
                    return secure_value
                
                # For backwards compatibility, try QB_PASSWORD if QBIT_PASSWORD was requested
                if var_name == 'QBIT_PASSWORD':
                    secure_value = credential_manager.get_credential('QB_PASSWORD')
                    if secure_value is not None:
                        return secure_value
                
            except Exception:
                pass
            
            # Fall back to environment variables
            return os.environ.get(var_name, match.group(0))
        
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, value)
    
    def _resolve_config_values(self, obj):
        """Recursively resolve environment variables in configuration object"""
        if isinstance(obj, str):
            return self._resolve_env_vars(obj)
        elif isinstance(obj, dict):
            return {key: self._resolve_config_values(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_config_values(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle dataclass instances
            for field_name in obj.__dict__:
                field_value = getattr(obj, field_name)
                resolved_value = self._resolve_config_values(field_value)
                setattr(obj, field_name, resolved_value)
            return obj
        else:
            return obj
    
    def get_resolved_config(self) -> AppConfig:
        """Get configuration with all environment variables and secure credentials resolved"""
        if not self.config:
            self.load_config()
        
        # Create a copy and resolve all variables
        import copy
        resolved_config = copy.deepcopy(self.config)
        if resolved_config:
            self._resolve_config_values(resolved_config)
            return resolved_config
        else:
            return self._create_default_config()
    
    def update_config(self, **kwargs) -> None:
        """Update configuration with new values"""
        if not self.config:
            self.load_config()
        
        # Update configuration attributes
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise ConfigError(f"Unknown configuration key: {key}")
    
    def get_last_folder(self) -> Optional[str]:
        """Get the last used folder path"""
        if self.config and not self.config.remember_last_folder:
            return None
            
        try:
            if self._last_folder_file.exists():
                return self._last_folder_file.read_text().strip()
        except Exception:
            pass
        return None
    
    def save_last_folder(self, folder_path: str) -> None:
        """Save the last used folder path"""
        if self.config and not self.config.remember_last_folder:
            return
            
        try:
            self._last_folder_file.parent.mkdir(parents=True, exist_ok=True)
            self._last_folder_file.write_text(folder_path)
        except Exception:
            pass  # Non-critical failure
    
    def validate_qbittorrent_config(self) -> tuple[bool, str]:
        """Validate qBittorrent configuration"""
        if not self.config:
            return False, "Configuration not loaded"
        
        qbit = self.config.qbittorrent
        
        # Check required fields
        if not qbit.host:
            return False, "qBittorrent host is required"
        if not (1 <= qbit.port <= 65535):
            return False, f"Invalid port: {qbit.port}"
        if not qbit.username:
            return False, "qBittorrent username is required"
        if not qbit.password:
            return False, "qBittorrent password is required"
        
        # Validate format
        try:
            TorrentFormat(self.config.torrent_creation.format)
        except ValueError:
            return False, f"Invalid torrent format: {self.config.torrent_creation.format}"
        
        return True, "Configuration is valid"
    
    def _create_default_config(self) -> AppConfig:
        """Create default configuration"""
        return AppConfig(
            qbittorrent=QBittorrentConfig(),
            torrent_creation=TorrentCreationConfig(),
            web_server=WebServerConfig()
        )
    
    def get_password(self) -> str:
        """Get password, resolving environment variables if needed"""
        config = self.get_config()  # This ensures config is loaded
        
        password = config.qbittorrent.password
        
        # Handle environment variable passwords
        if password.startswith('${') and password.endswith('}'):
            env_var = password[2:-1]
            env_password = os.getenv(env_var)
            if not env_password:
                raise ConfigError(f"Environment variable {env_var} not set")
            return env_password
        
        return password
    
    def resolve_environment_variables(self, value):
        """Resolve environment variables in any config value"""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            env_value = os.getenv(env_var)
            if env_value is None:
                raise ConfigError(f"Environment variable {env_var} not set")
            return env_value
        elif isinstance(value, list):
            return [self.resolve_environment_variables(item) for item in value]
        return value
    
    def get_trackers(self) -> list:
        """Get trackers list, resolving environment variables"""
        config = self.get_config()
        trackers = config.qbittorrent.trackers or []
        
        # Handle TRACKER environment variable as fallback
        if not trackers:
            tracker_env = os.getenv('TRACKER')
            if tracker_env:
                trackers = [tracker_env]
        
        # Resolve any environment variables in the tracker list
        return [self.resolve_environment_variables(tracker) for tracker in trackers]


class ConfigError(Exception):
    """Configuration related errors"""
    pass
