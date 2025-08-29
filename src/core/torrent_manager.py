"""
Torrent Manager
Uses qBittorrent v5.0.0+ Torrent Creator API for proper torrent creation
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import qbittorrentapi
from qbittorrentapi.torrentcreator import TaskStatus
from qbittorrentapi import exceptions as qba_exc

from ..core.config_manager import AppConfig
from ..utils.credential_manager import CredentialManager
from ..utils.docker_path_mapper import DockerPathMapper


class TorrentManager:
    """Manages torrent creation using qBittorrent v5.0.0+ Torrent Creator API"""
    
    def __init__(self, config: AppConfig, config_manager=None):
        self.config = config
        self.config_manager = config_manager
        self._qbit_client = None
        self._credential_manager = CredentialManager()
        
        # Initialize Docker path mapper - get mappings from qbittorrent.docker_path_mapping
        qbit_config = getattr(config, 'qbittorrent', None)
        print(f"DEBUG: qbit_config = {qbit_config}")
        if qbit_config and hasattr(qbit_config, 'docker_path_mapping'):
            docker_mapping = qbit_config.docker_path_mapping or {}
            print(f"DEBUG: Found docker_path_mapping in qbittorrent config: {docker_mapping}")
        else:
            # Fallback to top-level docker_mapping for backward compatibility
            docker_mapping_config = getattr(config, 'docker_mapping', {}) or {}
            docker_mapping = docker_mapping_config.get('mappings', {}) if docker_mapping_config else {}
            print(f"DEBUG: Using fallback docker_mapping: {docker_mapping}")
        
        print(f"DEBUG: Final docker_mapping passed to DockerPathMapper: {docker_mapping}")
        self._path_mapper = DockerPathMapper(docker_mapping)
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources, including qBittorrent client session"""
        if self._qbit_client:
            try:
                self._qbit_client.auth_log_out()
                print("🧹 Logged out from qBittorrent session")
            except Exception as e:
                print(f"Warning: Error during qBittorrent logout: {e}")
            finally:
                self._qbit_client = None
    
    async def _get_qbit_client(self):
        """Get or create qBittorrent client instance"""
        if self._qbit_client is None:
            try:
                # Get qBittorrent connection details
                qbit_config = self.config.qbittorrent
                
                # Get credentials using new auth structure
                username, password = self._resolve_credentials(qbit_config)
                
                if not username or not password:
                    raise Exception("qBittorrent credentials not found. Please configure them in the Settings page.")
                
                # Build the URL with proper scheme support
                scheme = 'https' if getattr(qbit_config, 'use_https', False) else 'http'
                base_path = getattr(qbit_config, 'base_path', '') or ''
                qbit_url = f"{scheme}://{qbit_config.host}:{qbit_config.port}{base_path}"
                
                print(f"Connecting to qBittorrent at {qbit_url} with user: {username}")
                
                # Create client instance with production-ready configuration
                verify_tls = getattr(qbit_config, 'verify_tls', True)
                connection_timeout = getattr(qbit_config, 'connection_timeout', 10.0)
                read_timeout = getattr(qbit_config, 'read_timeout', 30.0)
                pool_connections = getattr(qbit_config, 'pool_connections', 10)
                pool_maxsize = getattr(qbit_config, 'pool_maxsize', 10)
                
                self._qbit_client = qbittorrentapi.Client(
                    host=qbit_url,
                    username=username,
                    password=password,
                    VERIFY_WEBUI_CERTIFICATE=verify_tls,
                    # Production best practices from documentation
                    REQUESTS_ARGS={
                        "timeout": (connection_timeout, read_timeout),  # (connect, read) timeouts
                    },
                    HTTPADAPTER_ARGS={
                        "pool_connections": pool_connections,
                        "pool_maxsize": pool_maxsize,
                    },
                    RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
                    RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
                    DISABLE_LOGGING_DEBUG_OUTPUT=True,  # Reduce debug noise
                )
                
                # Test connection with proper exception handling
                try:
                    self._qbit_client.auth_log_in()
                    print("✅ Successfully authenticated with qBittorrent")
                except qba_exc.LoginFailed:
                    raise Exception("❌ Authentication failed. Please check your qBittorrent credentials.")
                except qba_exc.Forbidden403Error:
                    raise Exception("❌ IP address is banned from qBittorrent due to failed authentication attempts. Please wait or restart qBittorrent.")
                except qba_exc.Unauthorized401Error:
                    raise Exception("❌ Unauthorized. Please check your qBittorrent credentials and ensure Web UI is enabled.")
                except qba_exc.APIConnectionError as e:
                    raise Exception(f"❌ Cannot connect to qBittorrent Web UI at {qbit_url}. Error: {e}")
                
            except qba_exc.APIConnectionError as e:
                print(f"Connection error to qBittorrent: {e}")
                self._qbit_client = None
                raise Exception(f"Failed to connect to qBittorrent Web UI at {qbit_url}: {e}")
                
            except Exception as e:
                print(f"Failed to connect to qBittorrent: {e}")
                self._qbit_client = None
                raise
        
        return self._qbit_client
    
    def _resolve_credentials(self, qbit_config) -> tuple[Optional[str], Optional[str]]:
        """Resolve qBittorrent credentials based on auth configuration"""
        # Check if we have the new auth structure
        auth_config = getattr(qbit_config, 'auth', None)
        if auth_config:
            auth_mode = auth_config.get('mode', 'secret')
            if auth_mode == 'plain':
                # Use plain credentials from config
                username = auth_config.get('username', '')
                password = auth_config.get('password', '')
                print(f"DEBUG: Using plain auth - username: {username}, password: {'***' if password else 'empty'}")
                return username, password
            else:
                # Use secret references
                username_ref = auth_config.get('username_ref', 'QBIT_USERNAME')
                password_ref = auth_config.get('password_ref', 'QBIT_PASSWORD')
                username = self._credential_manager.get_credential(username_ref)
                password = self._credential_manager.get_credential(password_ref)
                print(f"DEBUG: Using secret auth - refs: {username_ref}/{password_ref}, resolved: {username}/{'***' if password else 'empty'}")
                return username, password
        
        # Fallback to legacy structure
        auth_mode = getattr(qbit_config, 'auth_mode', 'secret')
        if auth_mode == 'plain':
            username = getattr(qbit_config, 'username', '')
            password = getattr(qbit_config, 'password', '')
            print(f"DEBUG: Using legacy plain auth - username: {username}, password: {'***' if password else 'empty'}")
            return username, password
        else:
            # Use secret references with fallback to defaults
            username_ref = getattr(qbit_config, 'username_ref', 'QBIT_USERNAME')
            password_ref = getattr(qbit_config, 'password_ref', 'QBIT_PASSWORD')
            username = self._credential_manager.get_credential(username_ref)
            password = self._credential_manager.get_credential(password_ref)
            print(f"DEBUG: Using legacy secret auth - refs: {username_ref}/{password_ref}, resolved: {username}/{'***' if password else 'empty'}")
            return username, password
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test qBittorrent connection"""
        try:
            # Get qBittorrent connection details
            qbit_config = self.config.qbittorrent
            
            # Get credentials using new auth structure
            username, password = self._resolve_credentials(qbit_config)
            
            if not username or not password:
                missing = []
                if not username:
                    missing.append('username')
                if not password:
                    missing.append('password')
                
                return False, f"Missing qBittorrent credentials: {', '.join(missing)}. Please configure them in the Settings page."
            
            client = await self._get_qbit_client()
            
            # Get qBittorrent version info
            version_info = client.app.version
            webapi_version = client.app.webapiVersion
            
            # Check if torrent creator API is supported (v5.0.0+)
            version_parts = version_info.split('.')
            # Handle version strings that might start with 'v' (e.g., "v5.0.1")
            major_part = version_parts[0].lstrip('v') if len(version_parts) > 0 else '0'
            major_version = int(major_part) if major_part.isdigit() else 0
            minor_version = int(version_parts[1]) if len(version_parts) > 1 and version_parts[1].isdigit() else 0
            
            torrent_creator_supported = major_version >= 5
            
            message = f"Connected to qBittorrent {version_info}"
            if webapi_version:
                message += f" (Web API v{webapi_version})"
            
            if torrent_creator_supported:
                message += "\n✅ Torrent Creator API is supported"
            else:
                message += "\n⚠️  Torrent Creator API requires qBittorrent v5.0.0+"
            
            return True, message
            
        except qba_exc.LoginFailed:
            return False, "❌ Authentication failed. Please check your qBittorrent credentials."
        except qba_exc.Forbidden403Error:
            return False, "❌ IP address is banned from qBittorrent due to failed authentication attempts. Please wait or restart qBittorrent."
        except qba_exc.Unauthorized401Error:
            return False, "❌ Unauthorized. Please check your qBittorrent credentials and ensure Web UI is enabled."
        except qba_exc.APIConnectionError as e:
            return False, f"❌ Cannot connect to qBittorrent Web UI. Error: {e}"
        except qba_exc.UnsupportedQbittorrentVersion as e:
            return False, f"❌ qBittorrent version not supported by client library: {e}"
        except Exception as e:
            error_msg = str(e)
            return False, f"Connection failed: {error_msg}"
    
    async def create_torrent(
        self,
        source_path: str,
        output_dir: Optional[str] = None,
        private: Optional[bool] = None,
        start_seeding: Optional[bool] = None,
        format: Optional[str] = None,
        piece_size: Optional[int] = None,
        optimize_alignment: Optional[bool] = None,
        padded_file_size_limit: Optional[int] = None,
        comment: Optional[str] = None,
        trackers: Optional[List[str]] = None,
        url_seeds: Optional[List[str]] = None,
        source: Optional[str] = None  # Content description/source identifier
    ) -> Dict[str, Any]:
        """
        Create torrent using qBittorrent v5.0.0+ Torrent Creator API with full parameter support
        
        Args:
            source_path: Path to folder/file to create torrent from
            output_dir: Directory to save torrent file (optional for auto-seeding)
            private: Whether to create private torrent (defaults to config)
            start_seeding: Whether to start seeding immediately (defaults to config)
            format: Torrent format - 'v1', 'v2', or 'hybrid' (defaults to config)
            piece_size: Piece size in bytes (optional, qBittorrent chooses if None)
            optimize_alignment: Enforce optimized file alignment (defaults to config)
            padded_file_size_limit: Size threshold for padding files (defaults to config)
            comment: Comment embedded in torrent (defaults to config)
            trackers: List of tracker URLs (defaults to config/credentials)
            url_seeds: List of web seed URLs (HTTP/HTTPS mirrors)
            source: Content description/source identifier (custom field)
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Check if credentials are available first
            username = self._credential_manager.get_credential('QBIT_USERNAME')
            password = self._credential_manager.get_credential('QBIT_PASSWORD')
            
            if not username or not password:
                missing = []
                if not username:
                    missing.append('QBIT_USERNAME')
                if not password:
                    missing.append('QBIT_PASSWORD')
                
                return {
                    "success": False,
                    "error": f"Missing qBittorrent credentials: {', '.join(missing)}",
                    "message": "Please configure qBittorrent credentials in the Settings page"
                }
            
            client = await self._get_qbit_client()
            
            # Extract name from path for torrent naming
            source_name = Path(source_path).name
            
            # Resolve parameters from config if not provided
            torrent_config = self.config.torrent_creation
            qbit_config = self.config.qbittorrent
            
            # Use provided values or fall back to config defaults
            final_private = private if private is not None else torrent_config.private
            final_start_seeding = start_seeding if start_seeding is not None else torrent_config.start_seeding
            final_format = format if format is not None else torrent_config.format
            final_piece_size = piece_size if piece_size is not None else torrent_config.piece_size
            final_optimize_alignment = optimize_alignment if optimize_alignment is not None else torrent_config.optimize_alignment
            final_padded_file_size_limit = padded_file_size_limit if padded_file_size_limit is not None else torrent_config.padded_file_size_limit
            final_comment = comment if comment is not None else torrent_config.comment
            
            # Add source information to comment if provided
            if source:
                if final_comment:
                    final_comment = f"{final_comment} (Source: {source})"
                else:
                    final_comment = f"Source: {source}"
            
            print(f"Creating torrent with parameters:")
            print(f"  - Source: {source_name} {'(Source: ' + source + ')' if source else ''}")
            print(f"  - Private: {final_private}")
            print(f"  - Start seeding: {final_start_seeding}")
            print(f"  - Format: {final_format}")
            print(f"  - Piece size: {final_piece_size}")
            print(f"  - Optimize alignment: {final_optimize_alignment}")
            print(f"  - Padded file size limit: {final_padded_file_size_limit}")
            print(f"  - Comment: {final_comment}")
            
            # Convert host path to container path for qBittorrent
            container_source_path = self._path_mapper.host_to_container(source_path)
            
            print(f"Host path: {source_path}")
            print(f"Container path: {container_source_path}")
            
            if container_source_path != source_path:
                print(f"✅ Using Docker path mapping: {source_path} -> {container_source_path}")
            else:
                print("⚠️  No Docker path mapping found - using original path")
            
            # Resolve trackers - use provided trackers or get from credentials/config
            final_trackers = []
            if trackers:
                final_trackers = trackers
            else:
                # Get trackers from credential manager
                try:
                    credential_details = self._credential_manager.get_credential_details()
                    
                    # Ensure credential_details is not None and is a dictionary
                    if credential_details and isinstance(credential_details, dict):
                        # Get tracker URLs from stored credentials
                        for cred_key, details in credential_details.items():
                            if cred_key == 'TRACKER' and details and isinstance(details, dict) and details.get('exists'):
                                tracker_url = self._credential_manager.get_credential('TRACKER')
                                if tracker_url:
                                    final_trackers.append(tracker_url)
                    else:
                        print("Warning: credential_details is None or not a dictionary")
                                
                except Exception as e:
                    print(f"Warning: Could not load tracker credentials: {e}")
                
                # If no trackers from credentials, check config
                if not final_trackers and hasattr(self.config, 'qbittorrent') and self.config.qbittorrent.trackers:
                    final_trackers = self.config.qbittorrent.trackers
            
            # Resolve URL seeds - use provided URL seeds or get from config
            final_url_seeds = url_seeds if url_seeds else (torrent_config.url_seeds or [])
            
            print(f"  - Trackers: {final_trackers}")
            print(f"  - URL seeds: {final_url_seeds}")
            
            # Create torrent using qBittorrent's torrent creator API
            print(f"Creating torrent for: {container_source_path}")
            
            # Ensure format is one of the valid values
            if final_format == 'v1':
                torrent_format = 'v1'
            elif final_format == 'v2':
                torrent_format = 'v2'
            else:
                torrent_format = 'hybrid'
            
            print(f"Using torrent format: {torrent_format}")
            
            # Add torrent creation task using the correct API method with all parameters
            try:
                if final_start_seeding:
                    # Option 1: Let qBittorrent handle everything - no torrent_file_path needed
                    print("🎯 Using auto-seeding mode - qBittorrent will handle torrent file management")
                    task = client.torrentcreator.add_task(
                        source_path=container_source_path,
                        format=torrent_format,
                        start_seeding=final_start_seeding,
                        is_private=final_private,
                        optimize_alignment=final_optimize_alignment,
                        padded_file_size_limit=final_padded_file_size_limit,
                        piece_size=final_piece_size,
                        comment=final_comment,
                        trackers=final_trackers if final_trackers else None,
                        url_seeds=final_url_seeds if final_url_seeds else None
                    )
                else:
                    # Option 2: Save torrent file to a qBittorrent-accessible location
                    # Use qBittorrent's export directory or a known accessible path
                    if output_dir:
                        container_output_dir = self._path_mapper.host_to_container(output_dir)
                    else:
                        container_output_dir = "/data/downloads/torrents/qbittorrent/files"  # qBittorrent's export dir
                    
                    torrent_filename = f"{source_name}.torrent"
                    container_torrent_path = os.path.join(container_output_dir, torrent_filename)
                    
                    print(f"💾 Saving torrent file to: {container_torrent_path}")
                    task = client.torrentcreator.add_task(
                        source_path=container_source_path,
                        torrent_file_path=container_torrent_path,
                        format=torrent_format,
                        start_seeding=final_start_seeding,
                        is_private=final_private,
                        optimize_alignment=final_optimize_alignment,
                        padded_file_size_limit=final_padded_file_size_limit,
                        piece_size=final_piece_size,
                        comment=final_comment,
                        trackers=final_trackers if final_trackers else None,
                        url_seeds=final_url_seeds if final_url_seeds else None
                    )
            except qba_exc.Conflict409Error:
                return {
                    "success": False,
                    "error": "Too many torrent creation tasks running. Please wait for existing tasks to complete.",
                    "message": "qBittorrent is busy with other torrent creation tasks. Try again in a moment."
                }
            except qba_exc.NotFound404Error:
                return {
                    "success": False,
                    "error": f"Source path not found: {container_source_path}",
                    "message": f"qBittorrent cannot access the source path: {container_source_path}"
                }
            except Exception as e:
                print(f"Failed to create torrent task: {e}")
                # Try with minimal parameters as fallback
                print("Trying with minimal parameters...")
                try:
                    task = client.torrentcreator.add_task(
                        source_path=container_source_path
                    )
                except qba_exc.Conflict409Error:
                    return {
                        "success": False,
                        "error": "Too many torrent creation tasks running. Please wait for existing tasks to complete.",
                        "message": "qBittorrent is busy with other torrent creation tasks. Try again in a moment."
                    }
                except Exception as e2:
                    return {
                        "success": False,
                        "error": f"Failed to create torrent task: {e2}",
                        "message": f"Could not create torrent for {source_path}"
                    }
            
            # Wait for task completion
            task_id = task.taskID
            print(f"Torrent creation task started: {task_id}")
            
            # Poll task status until completion
            max_wait_time = 300  # 5 minutes max
            poll_interval = 2    # Check every 2 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
                
                # Get task status using the correct API method
                status = task.status()
                task_status = TaskStatus(status.status)
                
                print(f"Task status: {task_status.value}")
                
                if task_status == TaskStatus.FINISHED:
                    # Task completed successfully
                    print("Torrent creation completed successfully!")
                    
                    if start_seeding:
                        # qBittorrent handled everything - torrent is already added and seeding
                        print("🚀 Torrent automatically added to qBittorrent and seeding started!")
                        
                        # For auto-seeding mode, we don't need to save a file locally
                        # The torrent is managed entirely by qBittorrent
                        torrent_path = "Managed by qBittorrent (auto-seeding)"
                        torrent_hash = "auto-managed"
                        
                        # Try to get the hash from qBittorrent if possible
                        try:
                            # Get recent torrents to find our newly added one
                            torrents = client.torrents_info(limit=10, sort='added_on', reverse=True)
                            for torrent in torrents:
                                if source_name in torrent.name:
                                    torrent_hash = torrent.hash
                                    print(f"🔍 Found torrent in qBittorrent: {torrent.name} (Hash: {torrent_hash})")
                                    break
                        except Exception as e:
                            print(f"Warning: Could not retrieve torrent hash from qBittorrent: {e}")
                    
                    else:
                        # Check if torrent file was saved to the specified location
                        # Map back to host path for the response
                        torrent_filename = f"{source_name}.torrent"
                        
                        # The file was saved to qBittorrent's export directory
                        # Map the container path back to host path if possible
                        container_export_dir = "/data/downloads/torrents/qbittorrent/files"
                        host_export_dir = self._path_mapper.container_to_host(container_export_dir)
                        torrent_path = os.path.join(host_export_dir, torrent_filename)
                        
                        print(f"💾 Torrent file should be available at: {torrent_path}")
                        
                        # Try to calculate hash from saved file
                        try:
                            if os.path.exists(torrent_path):
                                with open(torrent_path, 'rb') as f:
                                    torrent_data = f.read()
                                import hashlib
                                torrent_hash = hashlib.sha1(torrent_data).hexdigest()
                                print(f"✅ Torrent file found and hash calculated: {torrent_hash}")
                            else:
                                print(f"⚠️  Torrent file not found at expected location: {torrent_path}")
                                torrent_hash = "file-not-accessible"
                        except Exception as e:
                            print(f"Warning: Could not access torrent file: {e}")
                            torrent_hash = "unknown"
                    
                    # Clean up task using the correct API method
                    try:
                        task.delete()
                        print(f"🧹 Cleaned up torrent creation task {task_id}")
                    except Exception as cleanup_error:
                        print(f"Warning: Could not cleanup task {task_id}: {cleanup_error}")
                    
                    return {
                        "success": True,
                        "torrent_hash": torrent_hash,
                        "torrent_path": torrent_path,
                        "task_id": task_id,
                        "auto_seeding": start_seeding,
                        "message": f"Torrent created successfully! {'Auto-seeding started in qBittorrent.' if start_seeding else f'Torrent file saved to: {torrent_path}'}"
                    }
                    
                elif task_status == TaskStatus.FAILED:
                    # Task failed
                    error_msg = getattr(status, 'errorMessage', 'Unknown error')
                    
                    print(f"Task failed with error: {error_msg}")
                    print(f"Full status object: {status}")
                    
                    try:
                        task.delete()
                        print(f"🧹 Cleaned up failed task {task_id}")
                    except Exception as cleanup_error:
                        print(f"Warning: Could not cleanup failed task {task_id}: {cleanup_error}")
                    
                    return {
                        "success": False,
                        "error": f"Torrent creation failed: {error_msg}",
                        "task_id": task_id,
                        "message": f"Failed to create torrent for {source_path}: {error_msg}"
                    }
            
            # Timeout reached
            print(f"⏰ Torrent creation timed out after {max_wait_time} seconds")
            try:
                task.delete()
                print(f"🧹 Cleaned up timed-out task {task_id}")
            except Exception as cleanup_error:
                print(f"Warning: Could not cleanup timed-out task {task_id}: {cleanup_error}")
                
            return {
                "success": False,
                "error": f"Torrent creation timed out after {max_wait_time} seconds",
                "task_id": task_id,
                "message": f"Torrent creation for {source_path} timed out"
            }
            
        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "error": f"Torrent creation failed: {error_msg}",
                "message": f"Could not create torrent for {source_path}"
            }
    
    async def get_torrent_file_bytes(self, task_id: str) -> Optional[bytes]:
        """
        Retrieve .torrent file bytes for a completed task
        
        Args:
            task_id: The task ID from torrent creation
            
        Returns:
            Torrent file bytes if successful, None otherwise
        """
        try:
            client = await self._get_qbit_client()
            torrent_bytes = client.torrentcreator.torrent_file(task_id=task_id)
            return torrent_bytes
        except qba_exc.Conflict409Error:
            print(f"Task {task_id} not yet finished or failed")
            return None
        except qba_exc.NotFound404Error:
            print(f"Task {task_id} not found")
            return None
        except Exception as e:
            print(f"Error retrieving torrent file bytes: {e}")
            return None
    
    async def get_torrent_creation_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a torrent creation task
        
        Args:
            task_id: The task ID from torrent creation
            
        Returns:
            Dictionary with task status information
        """
        try:
            client = await self._get_qbit_client()
            status_list = client.torrentcreator.status(task_id=task_id)
            
            if status_list and len(status_list) > 0:
                status = status_list[0]
                return {
                    "task_id": task_id,
                    "status": status.status,
                    "progress": getattr(status, 'progress', 0),
                    "error_message": getattr(status, 'errorMessage', ''),
                }
            else:
                return None
                
        except qba_exc.NotFound404Error:
            print(f"Task {task_id} not found")
            return None
        except Exception as e:
            print(f"Error getting task status: {e}")
            return None
    
    async def get_qbittorrent_info(self) -> Dict[str, Any]:
        """
        Get qBittorrent application information for monitoring
        
        Returns:
            Dictionary with version and build information
        """
        try:
            client = await self._get_qbit_client()
            
            # Get version information
            version = client.app.version
            web_api_version = client.app.web_api_version
            
            # Get build info if available
            try:
                build_info = client.app.build_info
            except Exception:
                build_info = {}
            
            # Get preferences (limited subset for monitoring)
            try:
                prefs = client.app.preferences
                monitoring_prefs = {
                    "web_ui_port": prefs.get("web_ui_port"),
                    "web_ui_https_enabled": prefs.get("web_ui_https_enabled"),
                    "dht": prefs.get("dht"),
                    "pex": prefs.get("pex"),
                    "lsd": prefs.get("lsd"),
                }
            except Exception:
                monitoring_prefs = {}
            
            return {
                "version": version,
                "web_api_version": web_api_version,
                "build_info": build_info,
                "preferences": monitoring_prefs,
                "torrent_creator_supported": True,  # We already validated this
            }
            
        except Exception as e:
            print(f"Error getting qBittorrent info: {e}")
            return {
                "error": str(e),
                "torrent_creator_supported": False,
            }

    # ========================================================================
    # NEW QBITTORRENT BROWSING METHODS
    # ========================================================================

    async def browse_qbittorrent_directory(self, path: str = "/") -> Dict[str, Any]:
        """
        Browse a directory using qBittorrent's API
        
        Args:
            path: Directory path to browse (from qBittorrent's perspective)
            
        Returns:
            Dictionary with directory contents and metadata
        """
        try:
            client = await self._get_qbit_client()
            
            # Normalize path for qBittorrent
            normalized_path = self._normalize_qbit_path(path)
            
            try:
                # Use qBittorrent's directory browsing API
                directory_contents = client.app_get_directory_content(normalized_path)
            except qba_exc.NotFound404Error:
                return {
                    "success": False,
                    "error": f"Directory not found or not accessible: {normalized_path}",
                    "current_path": normalized_path,
                    "entries": []
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"qBittorrent API error: {str(e)}",
                    "current_path": normalized_path,
                    "entries": []
                }
            
            # Process directory contents
            entries = []
            for item in directory_contents:
                item_str = str(item)
                is_directory = item_str.endswith('/')
                
                # Remove trailing slash for processing
                clean_name = item_str.rstrip('/')
                
                # Build full path
                if normalized_path.endswith('/'):
                    full_path = f"{normalized_path}{clean_name}"
                else:
                    full_path = f"{normalized_path}/{clean_name}"
                
                entries.append({
                    "name": clean_name,
                    "path": full_path,
                    "is_directory": is_directory,
                    "display_name": f"{clean_name}/" if is_directory else clean_name
                })
            
            # Sort entries: directories first, then files, both alphabetically
            entries.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
            
            # Calculate parent path
            parent_path = self._get_qbit_parent_path(normalized_path)
            
            return {
                "success": True,
                "current_path": normalized_path,
                "parent_path": parent_path,
                "entries": entries,
                "total_entries": len(entries),
                "navigation_mode": "qbittorrent"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error browsing directory: {str(e)}",
                "current_path": path,
                "entries": []
            }

    async def scan_qbittorrent_path(self, path: str) -> Dict[str, Any]:
        """
        Scan a path using qBittorrent's API to get metadata
        
        Args:
            path: Path to scan
            
        Returns:
            Dictionary with path metadata
        """
        try:
            client = await self._get_qbit_client()
            
            # First, try to browse the path as a directory
            browse_result = await self.browse_qbittorrent_directory(path)
            
            if browse_result["success"]:
                # It's a directory
                file_count = len([e for e in browse_result["entries"] if not e["is_directory"]])
                dir_count = len([e for e in browse_result["entries"] if e["is_directory"]])
                
                return {
                    "success": True,
                    "path": path,
                    "exists": True,
                    "is_directory": True,
                    "file_count": file_count,
                    "directory_count": dir_count,
                    "total_entries": len(browse_result["entries"]),
                    "navigation_mode": "qbittorrent",
                    # Note: qBittorrent directory listing doesn't provide size info
                    "total_bytes": 0,  # Would need recursive scan
                    "size_note": "Size calculation requires recursive scan"
                }
            else:
                # Try to browse parent to see if this is a file
                parent_path = self._get_qbit_parent_path(path)
                if parent_path:
                    parent_browse = await self.browse_qbittorrent_directory(parent_path)
                    if parent_browse["success"]:
                        filename = os.path.basename(path)
                        for entry in parent_browse["entries"]:
                            if entry["name"] == filename and not entry["is_directory"]:
                                return {
                                    "success": True,
                                    "path": path,
                                    "exists": True,
                                    "is_directory": False,
                                    "file_count": 1,
                                    "total_bytes": 0,  # qBittorrent doesn't provide file sizes in listing
                                    "navigation_mode": "qbittorrent",
                                    "size_note": "File size not available from directory listing"
                                }
                
                # Path doesn't exist or isn't accessible
                return {
                    "success": True,
                    "path": path,
                    "exists": False,
                    "is_directory": False,
                    "file_count": 0,
                    "total_bytes": 0,
                    "navigation_mode": "qbittorrent",
                    "error": browse_result.get("error", "Path not found")
                }
                
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "exists": False,
                "is_directory": False,
                "file_count": 0,
                "total_bytes": 0,
                "navigation_mode": "qbittorrent",
                "error": f"Error scanning path: {str(e)}"
            }

    async def get_qbittorrent_default_paths(self) -> List[str]:
        """
        Get commonly used default paths from qBittorrent
        
        Returns:
            List of default paths to offer in UI
        """
        try:
            client = await self._get_qbit_client()
            default_paths = ["/"]
            
            # Try to get qBittorrent's default save path
            try:
                default_save_path = client.app_default_save_path()
                if default_save_path and default_save_path != "/" and default_save_path not in default_paths:
                    default_paths.append(default_save_path)
            except Exception as e:
                print(f"Could not get default save path: {e}")
            
            # Try common container paths
            common_paths = ["/data", "/downloads", "/media", "/mnt", "/home"]
            for common_path in common_paths:
                try:
                    browse_result = await self.browse_qbittorrent_directory(common_path)
                    if browse_result["success"] and common_path not in default_paths:
                        default_paths.append(common_path)
                except Exception:
                    pass  # Path not accessible, skip it
            
            return default_paths
            
        except Exception as e:
            print(f"Error getting default paths: {e}")
            return ["/"]

    def _normalize_qbit_path(self, path: str) -> str:
        """Normalize a path for qBittorrent API"""
        if not path:
            return "/"
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = f"/{path}"
        
        # Remove double slashes
        while '//' in path:
            path = path.replace('//', '/')
        
        # Don't add trailing slash for root
        if path != "/" and path.endswith('/'):
            path = path.rstrip('/')
        
        return path

    def _get_qbit_parent_path(self, path: str) -> Optional[str]:
        """Get parent directory path for qBittorrent"""
        if not path or path == "/":
            return None
        
        parent = str(Path(path).parent)
        if parent == path:  # Already at root
            return None
        
        return parent if parent != "." else "/"

    async def analyze_qbittorrent_path(self, path: str, include_size: bool = True, recursive: bool = True) -> Dict[str, Any]:
        """
        Deep analysis of a path with optional recursive size calculation
        
        Args:
            path: Path to analyze
            include_size: Whether to calculate size information
            recursive: Whether to scan recursively for size calculation
            
        Returns:
            Dictionary with comprehensive path analysis
        """
        try:
            client = await self._get_qbit_client()
            
            # Start with basic path scan
            scan_result = await self.scan_qbittorrent_path(path)
            
            if not scan_result.get("success"):
                return scan_result
            
            # Enhanced analysis starts here
            analysis = {
                "success": True,
                "path": path,
                "exists": scan_result.get("exists", False),
                "is_directory": scan_result.get("is_directory", False),
                "basic_file_count": scan_result.get("file_count", 0),
                "navigation_mode": "qbittorrent"
            }
            
            if include_size and scan_result.get("is_directory") and recursive:
                # Perform recursive size calculation
                try:
                    recursive_stats = await self._calculate_recursive_stats(client, path)
                    analysis.update({
                        "total_bytes": recursive_stats.get("total_bytes", 0),
                        "total_file_count": recursive_stats.get("file_count", 0),
                        "total_directory_count": recursive_stats.get("directory_count", 0),
                        "max_depth": recursive_stats.get("max_depth", 0),
                        "largest_file": recursive_stats.get("largest_file"),
                        "scan_duration_ms": recursive_stats.get("scan_duration_ms", 0)
                    })
                except Exception as e:
                    print(f"Warning: Could not calculate recursive stats: {e}")
                    analysis.update({
                        "total_bytes": 0,
                        "total_file_count": scan_result.get("file_count", 0),
                        "size_calculation_error": str(e)
                    })
            else:
                # Basic stats only
                analysis.update({
                    "total_bytes": 0,
                    "total_file_count": scan_result.get("file_count", 0),
                    "size_note": "Recursive size calculation disabled"
                })
            
            return analysis
            
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": f"Path analysis failed: {str(e)}",
                "navigation_mode": "qbittorrent"
            }

    async def _calculate_recursive_stats(self, client, base_path: str, max_depth: int = 10) -> Dict[str, Any]:
        """
        Calculate recursive directory statistics using qBittorrent API
        
        Args:
            client: qBittorrent client
            base_path: Base directory to scan
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Dictionary with recursive statistics
        """
        import time
        start_time = time.time()
        
        stats = {
            "total_bytes": 0,
            "file_count": 0,
            "directory_count": 0,
            "max_depth": 0,
            "largest_file": None,
            "scan_duration_ms": 0
        }
        
        # Queue for breadth-first traversal: (path, depth)
        queue = [(base_path, 0)]
        visited = set()
        
        while queue and len(visited) < 1000:  # Limit to prevent runaway scans
            current_path, depth = queue.pop(0)
            
            if current_path in visited or depth > max_depth:
                continue
                
            visited.add(current_path)
            current_max_depth = stats["max_depth"]
            if isinstance(current_max_depth, int):
                stats["max_depth"] = max(current_max_depth, depth)
            else:
                stats["max_depth"] = depth
            
            try:
                # Browse current directory
                contents = client.app_get_directory_content(current_path)
                
                for item in contents:
                    item_str = str(item)
                    is_directory = item_str.endswith('/')
                    item_name = item_str.rstrip('/')
                    
                    if is_directory:
                        current_dir_count = stats["directory_count"]
                        if isinstance(current_dir_count, int):
                            stats["directory_count"] = current_dir_count + 1
                        else:
                            stats["directory_count"] = 1
                        # Add subdirectory to queue for recursive scanning
                        if current_path.endswith('/'):
                            full_path = f"{current_path}{item_name}"
                        else:
                            full_path = f"{current_path}/{item_name}"
                        queue.append((full_path, depth + 1))
                    else:
                        current_file_count = stats["file_count"]
                        if isinstance(current_file_count, int):
                            stats["file_count"] = current_file_count + 1
                        else:
                            stats["file_count"] = 1
                        # Note: qBittorrent directory API doesn't provide file sizes
                        # We could enhance this by getting file info, but it would be expensive
                        
            except Exception as e:
                print(f"Warning: Could not scan {current_path}: {e}")
                continue
        
        end_time = time.time()
        stats["scan_duration_ms"] = int((end_time - start_time) * 1000)
        
        return stats

    async def calculate_optimal_piece_size(self, path: str, target_pieces: int = 2500) -> Dict[str, Any]:
        """
        Calculate optimal piece size for a given path using intelligent algorithms
        
        Args:
            path: Path to analyze for piece size calculation
            target_pieces: Target number of pieces (default: 2500 for good ratio)
            
        Returns:
            Dictionary with piece size recommendations and analysis
        """
        try:
            # First get directory analysis with size information
            analysis = await self.analyze_qbittorrent_path(path, include_size=True, recursive=True)
            
            if not analysis.get("success"):
                return analysis
            
            total_bytes = analysis.get("total_bytes", 0)
            file_count = analysis.get("total_file_count", 0)
            
            # If we couldn't get size info, estimate based on file count
            if total_bytes == 0 and file_count > 0:
                # Rough estimation: assume average file size based on media type
                estimated_avg_size = 100 * 1024 * 1024  # 100MB average
                total_bytes = file_count * estimated_avg_size
                
            if total_bytes == 0:
                return {
                    "success": False,
                    "error": "Cannot determine content size for piece calculation",
                    "path": path
                }
            
            # Calculate intelligent piece sizes
            piece_calculations = self._calculate_piece_size_options(total_bytes, target_pieces, file_count)
            
            return {
                "success": True,
                "path": path,
                "total_bytes": total_bytes,
                "file_count": file_count,
                "target_pieces": target_pieces,
                "recommended": piece_calculations["recommended"],
                "options": piece_calculations["options"],
                "analysis": piece_calculations["analysis"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": f"Piece size calculation failed: {str(e)}"
            }

    def _calculate_piece_size_options(self, total_bytes: int, target_pieces: int, file_count: int) -> Dict[str, Any]:
        """
        Calculate multiple piece size options with intelligent recommendations
        
        Args:
            total_bytes: Total content size in bytes
            target_pieces: Target number of pieces
            file_count: Number of files
            
        Returns:
            Dictionary with piece size options and analysis
        """
        # Standard piece sizes (powers of 2, from 16KB to 32MB)
        standard_sizes = [
            16 * 1024,      # 16 KB
            32 * 1024,      # 32 KB  
            64 * 1024,      # 64 KB
            128 * 1024,     # 128 KB
            256 * 1024,     # 256 KB
            512 * 1024,     # 512 KB
            1024 * 1024,    # 1 MB
            2 * 1024 * 1024,    # 2 MB
            4 * 1024 * 1024,    # 4 MB
            8 * 1024 * 1024,    # 8 MB
            16 * 1024 * 1024,   # 16 MB
            32 * 1024 * 1024,   # 32 MB
        ]
        
        # Calculate ideal piece size for target pieces
        ideal_size = total_bytes // target_pieces
        
        # Find closest standard sizes
        options = []
        for size in standard_sizes:
            pieces = (total_bytes + size - 1) // size  # Ceiling division
            efficiency = self._calculate_piece_efficiency(total_bytes, size, pieces, file_count)
            
            options.append({
                "piece_size_bytes": size,
                "piece_size_human": self._format_bytes(size),
                "piece_count": pieces,
                "efficiency_score": efficiency["score"],
                "waste_percentage": efficiency["waste_percentage"],
                "network_efficiency": efficiency["network_efficiency"],
                "recommended_for": efficiency["recommended_for"]
            })
        
        # Sort by efficiency score (higher is better)
        options.sort(key=lambda x: x["efficiency_score"], reverse=True)
        
        # Find best option close to target
        recommended = options[0]  # Default to most efficient
        for option in options:
            piece_diff = abs(option["piece_count"] - target_pieces)
            current_diff = abs(recommended["piece_count"] - target_pieces)
            
            # Prefer options closer to target if efficiency is similar
            if piece_diff < current_diff and option["efficiency_score"] >= recommended["efficiency_score"] * 0.95:
                recommended = option
                break
        
        # Add analysis summary
        analysis = {
            "content_size_human": self._format_bytes(total_bytes),
            "file_count": file_count,
            "ideal_piece_size": self._format_bytes(ideal_size),
            "size_category": self._categorize_content_size(total_bytes),
            "recommendation_reason": self._get_recommendation_reason(recommended, total_bytes, file_count)
        }
        
        return {
            "recommended": recommended,
            "options": options[:8],  # Limit to top 8 options
            "analysis": analysis
        }

    def _calculate_piece_efficiency(self, total_bytes: int, piece_size: int, piece_count: int, file_count: int) -> Dict[str, Any]:
        """Calculate efficiency metrics for a piece size"""
        
        # Calculate waste (last piece padding)
        last_piece_bytes = total_bytes % piece_size
        if last_piece_bytes == 0:
            last_piece_bytes = piece_size
        waste_bytes = piece_size - last_piece_bytes
        waste_percentage = (waste_bytes / total_bytes) * 100
        
        # Network efficiency (fewer pieces = less overhead)
        # Optimal range is 1000-4000 pieces
        if 1000 <= piece_count <= 4000:
            network_efficiency = 100
        elif piece_count < 1000:
            network_efficiency = max(50, 100 - (1000 - piece_count) * 0.05)
        else:
            network_efficiency = max(50, 100 - (piece_count - 4000) * 0.01)
        
        # File alignment efficiency (prefer piece sizes that align well with typical file sizes)
        alignment_efficiency = 100
        if file_count > 1:
            avg_file_size = total_bytes / file_count
            if piece_size > avg_file_size * 2:
                alignment_efficiency -= 20  # Too large pieces for small files
            elif piece_size < avg_file_size / 10:
                alignment_efficiency -= 15  # Too small pieces for large files
        
        # Overall efficiency score
        score = (
            (100 - waste_percentage) * 0.3 +  # 30% waste minimization
            network_efficiency * 0.5 +        # 50% network efficiency  
            alignment_efficiency * 0.2        # 20% file alignment
        )
        
        # Determine what this size is recommended for
        recommended_for = []
        if piece_count < 500:
            recommended_for.append("small_content")
        elif 1000 <= piece_count <= 2500:
            recommended_for.append("optimal_range")
        elif piece_count > 4000:
            recommended_for.append("large_content")
        
        if waste_percentage < 1:
            recommended_for.append("minimal_waste")
        if network_efficiency > 95:
            recommended_for.append("fast_download")
        
        return {
            "score": round(score, 2),
            "waste_percentage": round(waste_percentage, 2),
            "network_efficiency": round(network_efficiency, 2),
            "alignment_efficiency": round(alignment_efficiency, 2),
            "recommended_for": recommended_for
        }

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human readable string"""
        count = float(bytes_count)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if count < 1024.0:
                return f"{count:.1f} {unit}"
            count /= 1024.0
        return f"{count:.1f} PB"

    def _categorize_content_size(self, total_bytes: int) -> str:
        """Categorize content size for recommendations"""
        if total_bytes < 100 * 1024 * 1024:  # < 100MB
            return "small"
        elif total_bytes < 1024 * 1024 * 1024:  # < 1GB
            return "medium"
        elif total_bytes < 10 * 1024 * 1024 * 1024:  # < 10GB
            return "large"
        else:
            return "very_large"

    def _get_recommendation_reason(self, recommended: Dict[str, Any], total_bytes: int, file_count: int) -> str:
        """Generate human-readable recommendation reason"""
        size_cat = self._categorize_content_size(total_bytes)
        piece_count = recommended["piece_count"]
        
        if "optimal_range" in recommended.get("recommended_for", []):
            return f"Optimal balance of {piece_count} pieces for efficient downloading and minimal waste"
        elif "minimal_waste" in recommended.get("recommended_for", []):
            return f"Minimizes wasted space with only {recommended['waste_percentage']:.1f}% padding"
        elif size_cat == "small":
            return f"Appropriate for small content to avoid excessive piece overhead"
        elif size_cat == "very_large":
            return f"Efficient for large content with {piece_count} manageable pieces"
        else:
            return f"Good balance of {piece_count} pieces for {size_cat} content size"
