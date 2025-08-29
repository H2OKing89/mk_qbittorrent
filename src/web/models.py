"""
Pydantic models for the web API
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

# ====== NAVIGATION MODE ENUM ======

class NavigationMode(str, Enum):
    """Navigation mode for path browsing"""
    LOCAL = "local"          # Local filesystem with Docker path mapping (legacy)
    QBITTORRENT = "qbittorrent"  # Direct qBittorrent API browsing (new)

# ====== EXISTING MODELS ======

class TorrentCreateRequest(BaseModel):
    source_path: str
    # ... other existing fields

class ScanRequest(BaseModel):
    path: str
    mode: Optional[NavigationMode] = NavigationMode.LOCAL  # Default to legacy for compatibility

class ScanResponse(BaseModel):
    totalBytes: int
    fileCount: int
    exists: bool
    mode: str  # 'file' or 'folder'
    error: Optional[str] = None
    navigation_mode: Optional[NavigationMode] = NavigationMode.LOCAL  # Track which mode was used

# ====== NEW QBITTORRENT BROWSING MODELS ======

class QBitDirectoryEntry(BaseModel):
    """Represents a file or directory entry from qBittorrent"""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None  # None for directories
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        if self.is_directory and not self.name.endswith('/'):
            return f"{self.name}/"
        return self.name

class QBitBrowseRequest(BaseModel):
    """Request to browse a directory through qBittorrent"""
    path: str = Field(default="/", description="Directory path to browse")

class QBitBrowseResponse(BaseModel):
    """Response from qBittorrent directory browsing"""
    current_path: str
    parent_path: Optional[str] = None
    entries: List[QBitDirectoryEntry]
    error: Optional[str] = None
    success: bool = True
    total_entries: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.success and 'total_entries' not in data:
            self.total_entries = len(self.entries)

class QBitScanRequest(BaseModel):
    """Request to scan a path through qBittorrent"""
    path: str

class QBitScanResponse(BaseModel):
    """Response from qBittorrent path scanning"""
    path: str
    exists: bool
    is_directory: bool
    total_bytes: int = 0
    file_count: int = 0
    error: Optional[str] = None
    success: bool = True

# ====== UNIFIED BROWSING MODELS ======

class UnifiedBrowseRequest(BaseModel):
    """Unified request for browsing directories (supports both modes)"""
    path: str = Field(default="/", description="Directory path to browse")
    mode: NavigationMode = Field(default=NavigationMode.QBITTORRENT, description="Navigation mode")

class UnifiedBrowseEntry(BaseModel):
    """Unified directory entry (works for both local and qBittorrent)"""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    source_mode: NavigationMode  # Track which system provided this entry
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        if self.is_directory and not self.name.endswith('/'):
            return f"{self.name}/"
        return self.name

class UnifiedBrowseResponse(BaseModel):
    """Unified response for directory browsing"""
    current_path: str
    parent_path: Optional[str] = None
    entries: List[UnifiedBrowseEntry]
    mode: NavigationMode
    error: Optional[str] = None
    success: bool = True
    total_entries: int = 0
    
    # Mode-specific metadata
    docker_mapping_info: Optional[Dict[str, Any]] = None  # For local mode
    qbittorrent_info: Optional[Dict[str, Any]] = None     # For qBittorrent mode
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.success and 'total_entries' not in data:
            self.total_entries = len(self.entries)

# ====== RESPONSE MODELS FOR WEB API ======

class PiecesRequest(BaseModel):
    """Request for piece size calculation"""
    total_bytes: int
    desired_piece_size: Optional[int] = None
    target_piece_count: Optional[int] = None

class PiecesResponse(BaseModel):
    """Response with piece size calculation"""
    piece_size_bytes: int
    piece_count: int
    target_achieved: bool = True

class TorrentCreationRequest(BaseModel):
    """Enhanced torrent creation request"""
    source_path: str
    output_dir: Optional[str] = None
    private: Optional[bool] = True
    start_seeding: Optional[bool] = False
    format: Optional[str] = "v1"
    piece_size: Optional[int] = None
    optimize_alignment: Optional[bool] = None
    padded_file_size_limit: Optional[int] = None
    comment: Optional[str] = None
    trackers: Optional[List[str]] = None
    url_seeds: Optional[List[str]] = None
    source: Optional[str] = None
    navigation_mode: Optional[NavigationMode] = NavigationMode.QBITTORRENT  # Track how path was selected

class UserPreference(BaseModel):
    """User preference storage model"""
    key: str
    value: Any
    user_id: str = "default"
