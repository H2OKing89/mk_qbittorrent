"""
qBittorrent Directory Browsing Service
Provides filesystem navigation through qBittorrent API
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from qbittorrentapi import exceptions as qba_exc

from ..web.models import (
    QBitDirectoryEntry, 
    QBitBrowseResponse, 
    QBitScanResponse,
    UnifiedBrowseEntry,
    UnifiedBrowseResponse,
    NavigationMode
)


class QBitBrowsingService:
    """Service for browsing directories through qBittorrent API"""
    
    def __init__(self, qbit_client):
        self.qbit_client = qbit_client
        
    async def browse_directory(self, path: str = "/") -> QBitBrowseResponse:
        """
        Browse a directory using qBittorrent API
        
        Args:
            path: Directory path to browse (from qBittorrent's perspective)
            
        Returns:
            QBitBrowseResponse with directory contents
        """
        try:
            # Ensure we have a qBittorrent client
            if not self.qbit_client:
                return QBitBrowseResponse(
                    current_path=path,
                    entries=[],
                    success=False,
                    error="qBittorrent client not available"
                )
            
            # Normalize path
            normalized_path = self._normalize_path(path)
            
            # Call qBittorrent API to get directory contents
            try:
                directory_contents = self.qbit_client.app_get_directory_content(normalized_path)
            except qba_exc.NotFound404Error:
                return QBitBrowseResponse(
                    current_path=normalized_path,
                    entries=[],
                    success=False,
                    error=f"Directory not found or not accessible: {normalized_path}"
                )
            except Exception as e:
                return QBitBrowseResponse(
                    current_path=normalized_path,
                    entries=[],
                    success=False,
                    error=f"qBittorrent API error: {str(e)}"
                )
            
            # Convert response to our format
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
                
                entry = QBitDirectoryEntry(
                    name=clean_name,
                    path=full_path,
                    is_directory=is_directory,
                    size=None if is_directory else 0  # qBittorrent doesn't provide size in listing
                )
                entries.append(entry)
            
            # Sort entries: directories first, then files, both alphabetically
            entries.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            
            # Calculate parent path
            parent_path = self._get_parent_path(normalized_path)
            
            return QBitBrowseResponse(
                current_path=normalized_path,
                parent_path=parent_path,
                entries=entries,
                success=True
            )
            
        except Exception as e:
            return QBitBrowseResponse(
                current_path=path,
                entries=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    async def scan_path(self, path: str) -> QBitScanResponse:
        """
        Scan a path to get metadata (size, file count, etc.)
        
        Args:
            path: Path to scan
            
        Returns:
            QBitScanResponse with path metadata
        """
        try:
            # For qBittorrent scanning, we need to try browsing the path
            # to see if it exists and is accessible
            
            # First, try to browse the path directly
            browse_result = await self.browse_directory(path)
            
            if browse_result.success:
                # It's a directory
                # For file count and size, we'd need to recursively scan
                # For now, just return basic info
                return QBitScanResponse(
                    path=path,
                    exists=True,
                    is_directory=True,
                    total_bytes=0,  # Would need recursive scan
                    file_count=len([e for e in browse_result.entries if not e.is_directory]),
                    success=True
                )
            else:
                # Try to browse parent to see if this is a file
                parent_path = self._get_parent_path(path)
                if parent_path:
                    parent_browse = await self.browse_directory(parent_path)
                    if parent_browse.success:
                        # Check if our path is in the parent's listing
                        filename = os.path.basename(path)
                        for entry in parent_browse.entries:
                            if entry.name == filename and not entry.is_directory:
                                return QBitScanResponse(
                                    path=path,
                                    exists=True,
                                    is_directory=False,
                                    total_bytes=entry.size or 0,
                                    file_count=1,
                                    success=True
                                )
                
                # Path doesn't exist or isn't accessible
                return QBitScanResponse(
                    path=path,
                    exists=False,
                    is_directory=False,
                    total_bytes=0,
                    file_count=0,
                    success=True
                )
                
        except Exception as e:
            return QBitScanResponse(
                path=path,
                exists=False,
                is_directory=False,
                total_bytes=0,
                file_count=0,
                success=False,
                error=f"Error scanning path: {str(e)}"
            )
    
    async def get_default_paths(self) -> List[str]:
        """
        Get commonly used default paths from qBittorrent
        
        Returns:
            List of default paths to offer in UI
        """
        try:
            default_paths = ["/"]
            
            # Try to get qBittorrent's default save path
            if self.qbit_client:
                try:
                    default_save_path = self.qbit_client.app_default_save_path()
                    if default_save_path and default_save_path != "/":
                        default_paths.append(default_save_path)
                except:
                    pass
                
                # Try common container paths
                common_paths = ["/data", "/downloads", "/media", "/mnt"]
                for common_path in common_paths:
                    try:
                        browse_result = await self.browse_directory(common_path)
                        if browse_result.success and common_path not in default_paths:
                            default_paths.append(common_path)
                    except:
                        pass
            
            return default_paths
            
        except Exception:
            return ["/"]
    
    def _normalize_path(self, path: str) -> str:
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
    
    def _get_parent_path(self, path: str) -> Optional[str]:
        """Get parent directory path"""
        if not path or path == "/":
            return None
        
        parent = str(Path(path).parent)
        if parent == path:  # Already at root
            return None
        
        return parent if parent != "." else "/"


class UnifiedBrowsingService:
    """Service that provides unified browsing across both local and qBittorrent modes"""
    
    def __init__(self, qbit_browsing_service: QBitBrowsingService, docker_path_mapper=None):
        self.qbit_service = qbit_browsing_service
        self.docker_path_mapper = docker_path_mapper
    
    async def browse_directory(self, path: str, mode: NavigationMode) -> UnifiedBrowseResponse:
        """
        Browse directory using specified mode
        
        Args:
            path: Directory path to browse
            mode: Navigation mode (local or qbittorrent)
            
        Returns:
            UnifiedBrowseResponse with directory contents
        """
        if mode == NavigationMode.QBITTORRENT:
            return await self._browse_qbittorrent(path)
        else:
            return await self._browse_local(path)
    
    async def _browse_qbittorrent(self, path: str) -> UnifiedBrowseResponse:
        """Browse using qBittorrent API"""
        qbit_result = await self.qbit_service.browse_directory(path)
        
        # Convert to unified format
        unified_entries = [
            UnifiedBrowseEntry(
                name=entry.name,
                path=entry.path,
                is_directory=entry.is_directory,
                size=entry.size,
                source_mode=NavigationMode.QBITTORRENT
            )
            for entry in qbit_result.entries
        ]
        
        return UnifiedBrowseResponse(
            current_path=qbit_result.current_path,
            parent_path=qbit_result.parent_path,
            entries=unified_entries,
            mode=NavigationMode.QBITTORRENT,
            error=qbit_result.error,
            success=qbit_result.success,
            qbittorrent_info={
                "api_accessible": qbit_result.success,
                "total_entries": len(unified_entries)
            }
        )
    
    async def _browse_local(self, path: str) -> UnifiedBrowseResponse:
        """Browse using local filesystem (legacy mode)"""
        try:
            from ..utils.file_utils import get_folder_info
            
            # This would need to be implemented to maintain backward compatibility
            # For now, return a placeholder
            return UnifiedBrowseResponse(
                current_path=path,
                entries=[],
                mode=NavigationMode.LOCAL,
                error="Local browsing not yet implemented in unified service",
                success=False,
                docker_mapping_info={
                    "mapper_available": self.docker_path_mapper is not None,
                    "path_mapped": self.docker_path_mapper.is_path_mapped(path) if self.docker_path_mapper else False
                }
            )
            
        except Exception as e:
            return UnifiedBrowseResponse(
                current_path=path,
                entries=[],
                mode=NavigationMode.LOCAL,
                error=f"Local browsing error: {str(e)}",
                success=False
            )
