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
                
                # Create client instance
                verify_tls = getattr(qbit_config, 'verify_tls', True)
                self._qbit_client = qbittorrentapi.Client(
                    host=qbit_url,
                    username=username,
                    password=password,
                    VERIFY_WEBUI_CERTIFICATE=verify_tls
                )
                
                # Test connection
                self._qbit_client.auth_log_in()
                print("✅ Successfully authenticated with qBittorrent")
                
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
            
        except Exception as e:
            error_msg = str(e)
            if "Unauthorized" in error_msg or "401" in error_msg:
                return False, f"❌ Authentication failed. Please check your qBittorrent credentials."
            elif "Forbidden" in error_msg or "IP address is banned" in error_msg:
                return False, f"❌ IP address is banned from qBittorrent due to failed authentication attempts. Please wait or restart qBittorrent."
            else:
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
            except Exception as e:
                print(f"Failed to create torrent task: {e}")
                # Try with minimal parameters
                print("Trying with minimal parameters...")
                try:
                    task = client.torrentcreator.add_task(
                        source_path=container_source_path
                    )
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
                    task.delete()
                    
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
                    
                    task.delete()
                    
                    return {
                        "success": False,
                        "error": f"Torrent creation failed: {error_msg}",
                        "task_id": task_id,
                        "message": f"Failed to create torrent for {source_path}: {error_msg}"
                    }
            
            # Timeout reached
            try:
                task.delete()
            except:
                pass  # Task might already be gone
                
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
