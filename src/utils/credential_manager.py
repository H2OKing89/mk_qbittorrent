"""
Secure Credential Manager
Handles encryption and storage of sensitive configuration data
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class CredentialManager:
    """Manages encrypted storage of sensitive credentials"""
    
    def __init__(self, credentials_file: str = "config/.credentials"):
        self.credentials_file = Path(credentials_file)
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        self._key = None
        
    def _get_machine_key(self) -> bytes:
        """Generate a machine-specific encryption key"""
        # Use machine-specific data to create a consistent key
        machine_data = (
            os.uname().nodename +  # hostname
            str(os.path.getsize('/proc/cpuinfo') if Path('/proc/cpuinfo').exists() else '0') +
            str(self.credentials_file.parent.absolute())
        ).encode()
        
        # Create a salt from the machine data
        salt = hashlib.sha256(machine_data).digest()[:16]
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_data))
        return key
    
    def _get_cipher(self) -> Fernet:
        """Get the encryption cipher"""
        if self._key is None:
            self._key = self._get_machine_key()
        return Fernet(self._key)
    
    def store_credential(self, key: str, value: str, custom_name: Optional[str] = None) -> bool:
        """Store an encrypted credential with optional custom name"""
        try:
            # Load existing credentials
            credentials = self._load_credentials()
            
            # Encrypt the value
            cipher = self._get_cipher()
            encrypted_value = cipher.encrypt(value.encode())
            
            # Store the encrypted value and metadata
            credential_data = {
                'value': base64.urlsafe_b64encode(encrypted_value).decode(),
                'custom_name': custom_name
            }
            
            credentials[key] = credential_data
            
            # Save to file
            return self._save_credentials(credentials)
            
        except Exception as e:
            print(f"Error storing credential {key}: {e}")
            return False
    
    def get_credential(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a credential"""
        try:
            credentials = self._load_credentials()
            
            if key not in credentials:
                # Fallback to .env file for testing
                try:
                    from dotenv import load_dotenv
                    import os
                    
                    # Load .env file from config directory
                    env_path = Path(__file__).parent.parent.parent / "config" / ".env"
                    if env_path.exists():
                        load_dotenv(env_path)
                        env_value = os.getenv(key)
                        if env_value:
                            print(f"DEBUG: Using .env fallback for {key}")
                            return env_value
                except Exception as env_e:
                    print(f"DEBUG: .env fallback failed for {key}: {env_e}")
                
                return None
            
            credential_data = credentials[key]
            
            # Handle both old format (string) and new format (dict)
            if isinstance(credential_data, str):
                encrypted_value = base64.urlsafe_b64decode(credential_data.encode())
            else:
                encrypted_value = base64.urlsafe_b64decode(credential_data['value'].encode())
            
            # Decrypt the value
            cipher = self._get_cipher()
            decrypted_value = cipher.decrypt(encrypted_value)
            
            print(f"DEBUG: Using secure storage for {key}")
            return decrypted_value.decode()
            
        except Exception as e:
            print(f"Error retrieving credential {key}: {e}")
            # Fallback to .env file for testing
            try:
                from dotenv import load_dotenv
                import os
                
                # Load .env file from config directory
                env_path = Path(__file__).parent.parent.parent / "config" / ".env"
                if env_path.exists():
                    load_dotenv(env_path)
                    env_value = os.getenv(key)
                    if env_value:
                        print(f"DEBUG: Using .env fallback for {key} (after error)")
                        return env_value
            except Exception as env_e:
                print(f"DEBUG: .env fallback failed for {key}: {env_e}")
            
            return None
    
    def delete_credential(self, key: str) -> bool:
        """Delete a credential"""
        try:
            credentials = self._load_credentials()
            
            if key in credentials:
                del credentials[key]
                return self._save_credentials(credentials)
            
            return True
            
        except Exception as e:
            print(f"Error deleting credential {key}: {e}")
            return False
    
    def list_credentials(self) -> list:
        """List all stored credential keys (not values)"""
        try:
            credentials = self._load_credentials()
            return list(credentials.keys())
        except Exception:
            return []
    
    def has_credential(self, key: str) -> bool:
        """Check if a credential exists"""
        return key in self._load_credentials()
    
    def get_credential_custom_name(self, key: str) -> Optional[str]:
        """Get the custom name for a credential"""
        try:
            credentials = self._load_credentials()
            if key not in credentials:
                return None
            
            credential_data = credentials[key]
            if isinstance(credential_data, dict):
                return credential_data.get('custom_name')
            return None
        except Exception:
            return None
    
    def mask_tracker_url(self, url: str) -> str:
        """Mask sensitive parts of tracker URLs"""
        if not url or not isinstance(url, str):
            return ''
        
        import re
        
        # Pattern to match common tracker URL formats
        patterns = [
            # https://tracker.domain.com/PASSKEY/announce
            (r'^(https?://[^/]+/)([^/]{20,})(/.*)?$', r'\1########\3'),
            # https://tracker.domain.com/announce.php?passkey=PASSKEY&...
            (r'^(https?://[^?]+\?[^=]*=)([^&]{20,})(.*)$', r'\1########\3'),
        ]
        
        for pattern, replacement in patterns:
            match = re.match(pattern, url)
            if match:
                return re.sub(pattern, replacement, url)
        
        # Fallback: just show the domain part
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}/########{'#' * 8}/announce"
        except Exception:
            return 'Invalid URL format'
    
    def get_credential_details(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all credentials"""
        details = {}
        credentials = self._load_credentials()
        
        important_creds = ['TRACKER', 'QBIT_USERNAME', 'QBIT_PASSWORD']
        
        for cred in important_creds:
            exists = cred in credentials
            custom_name = None
            masked_value = None
            
            if exists:
                credential_data = credentials[cred]
                if isinstance(credential_data, dict):
                    custom_name = credential_data.get('custom_name')
                
                # Get masked value for display
                if cred == 'TRACKER':
                    actual_value = self.get_credential(cred)
                    if actual_value:
                        masked_value = self.mask_tracker_url(actual_value)
                elif cred == 'QBIT_PASSWORD':
                    # Mask password for security
                    actual_value = self.get_credential(cred)
                    if actual_value:
                        masked_value = '*' * len(actual_value)
                elif cred == 'QBIT_USERNAME':
                    # Username can be shown
                    actual_value = self.get_credential(cred)
                    if actual_value:
                        masked_value = actual_value
            
            details[cred] = {
                'exists': exists,
                'custom_name': custom_name,
                'masked_value': masked_value
            }
        
        return details
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from file"""
        if not self.credentials_file.exists():
            return {}
        
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Save credentials to file"""
        try:
            # Create backup if file exists
            if self.credentials_file.exists():
                backup_file = self.credentials_file.with_suffix('.credentials.bak')
                self.credentials_file.rename(backup_file)
            
            # Write new credentials
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(self.credentials_file, 0o600)
            
            return True
            
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False
    
    def migrate_from_env(self, env_file: str = "config/.env") -> bool:
        """Migrate credentials from .env file to encrypted storage"""
        env_path = Path(env_file)
        if not env_path.exists():
            return True  # Nothing to migrate
        
        try:
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            migrated_keys = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Migrate important credentials, normalize QB_PASSWORD to QBIT_PASSWORD
                    if key in ['QBIT_PASSWORD', 'QB_PASSWORD', 'TRACKER']:
                        # Normalize QB_PASSWORD to QBIT_PASSWORD for consistency
                        if key == 'QB_PASSWORD':
                            key = 'QBIT_PASSWORD'
                        
                        if self.store_credential(key, value):
                            migrated_keys.append(key)
            
            if migrated_keys:
                print(f"✅ Migrated {len(migrated_keys)} credentials to encrypted storage")
                
                # Create backup of .env file
                backup_path = env_path.with_suffix('.env.bak')
                env_path.rename(backup_path)
                print(f"📁 Backed up .env file to {backup_path}")
                
                return True
            
        except Exception as e:
            print(f"Error migrating from .env: {e}")
            return False
        
        return True
    
    def export_for_config(self) -> Dict[str, str]:
        """Export credentials in a format suitable for config resolution"""
        credentials = {}
        for key in self.list_credentials():
            value = self.get_credential(key)
            if value:
                credentials[key] = value
        return credentials


class SecureConfigManager:
    """Enhanced config manager that uses encrypted credential storage"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from core.config_manager import ConfigManager
        
        self.config_manager = ConfigManager(config_path)
        self.credential_manager = CredentialManager()
        
        # Auto-migrate from .env if it exists
        self.credential_manager.migrate_from_env()
    
    def resolve_env_vars(self, text: str) -> str:
        """Resolve environment variables using encrypted credentials first, then system env"""
        if not isinstance(text, str) or '${' not in text:
            return text
        
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            
            # Try encrypted credentials first
            value = self.credential_manager.get_credential(var_name)
            if value is not None:
                return value
            
            # Fall back to system environment variables
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, text)
    
    def store_secure_value(self, key: str, value: str) -> bool:
        """Store a secure value in encrypted storage"""
        return self.credential_manager.store_credential(key, value)
    
    def get_secure_value(self, key: str) -> Optional[str]:
        """Get a secure value from encrypted storage"""
        return self.credential_manager.get_credential(key)
    
    def get_credential_status(self) -> Dict[str, bool]:
        """Get status of important credentials"""
        important_creds = ['TRACKER', 'QBIT_PASSWORD']
        status = {}
        
        for cred in important_creds:
            status[cred] = self.credential_manager.has_credential(cred)
        
        return status
