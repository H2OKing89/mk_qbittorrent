"""
FastAPI Web Application for Easy Torrent Creator
Provides REST API for settings management, torrent creation, and monitoring
"""
import os
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from contextlib import asynccontextmanager
import math
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from fastapi.responses import Response

# Import our application modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.config_manager import ConfigManager, AppConfig
from src.core.torrent_manager import TorrentManager
from src.utils.credential_manager import CredentialManager, SecureConfigManager
from src.utils.settings_storage import SettingsStorageManager, SettingsValidator
from src.web.models import (
    NavigationMode, 
    QBitBrowseRequest, QBitBrowseResponse,
    UnifiedBrowseRequest, UnifiedBrowseResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global managers
config_manager: Optional[ConfigManager] = None
secure_config_manager: Optional[SecureConfigManager] = None
torrent_manager: Optional[TorrentManager] = None
settings_storage: Optional[SettingsStorageManager] = None


def ensure_managers_initialized():
    """Ensure all managers are initialized, raise error if not"""
    global config_manager, secure_config_manager, torrent_manager, settings_storage
    if any(manager is None for manager in [config_manager, secure_config_manager, torrent_manager, settings_storage]):
        raise HTTPException(status_code=503, detail="Application managers not initialized")

def get_settings_storage():
    """Get settings storage with type assertion"""
    ensure_managers_initialized()
    assert settings_storage is not None
    return settings_storage

def get_secure_config_manager():
    """Get secure config manager with type assertion"""
    ensure_managers_initialized()
    assert secure_config_manager is not None
    return secure_config_manager

def get_torrent_manager():
    """Get torrent manager with type assertion"""
    ensure_managers_initialized()
    assert torrent_manager is not None
    return torrent_manager

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    global config_manager, secure_config_manager, torrent_manager, settings_storage
    
    try:
        # Initialize configuration managers
        config_manager = ConfigManager()
        secure_config_manager = SecureConfigManager()
        settings_storage = SettingsStorageManager()
        
        # Initialize torrent manager
        config = config_manager.load_config()
        torrent_manager = TorrentManager(config, config_manager)
        
        logger.info("✅ Application managers initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        if torrent_manager:
            await torrent_manager.cleanup()
        logger.info("✅ Application cleanup completed")
    except Exception as e:
        logger.error(f"Warning: Cleanup error: {e}")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Easy Torrent Creator API",
    description="REST API for torrent creation and settings management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

# Pydantic models for API requests
class SettingsUpdateRequest(BaseModel):
    section: str  # 'qbittorrent', 'torrent_creation', 'web_server', etc.
    settings: Dict[str, Any]
    persist: bool = True  # Whether to save to persistent storage

class CredentialRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class TorrentCreationRequest(BaseModel):
    source_path: str
    torrent_name: Optional[str] = None
    private: Optional[bool] = None
    start_seeding: Optional[bool] = None
    format: Optional[str] = None
    piece_size: Optional[int] = None
    optimize_alignment: Optional[bool] = None
    padded_file_size_limit: Optional[int] = None
    comment: Optional[str] = None
    trackers: Optional[List[str]] = None
    url_seeds: Optional[List[str]] = None
    source: Optional[str] = None

# New request models for missing endpoints

class ScanRequest(BaseModel):
    path: str

class ScanResponse(BaseModel):
    totalBytes: int
    fileCount: int
    exists: bool
    mode: str  # 'file' or 'folder'
    error: Optional[str] = None

class PiecesRequest(BaseModel):
    totalBytes: int
    desiredPieceSize: Optional[int] = None
    target: Optional[int] = 2500

class PiecesResponse(BaseModel):
    pieceSizeBytes: int
    pieceCount: int

class CreateTorrentRequest(BaseModel):
    """Enhanced torrent creation request matching the spec"""
    # Path selection
    mode: str  # 'file' or 'folder'
    path: str
    
    # Piece settings
    pieceSizeMode: str  # 'auto' or 'manual'
    pieceSizeBytes: Optional[int] = None
    targetPieces: int = 2500
    
    # Privacy and seeding
    privateTorrent: bool = True
    startSeeding: bool = False
    ignoreShareRatio: bool = False
    
    # Alignment
    optimizeAlignment: bool = False
    alignThresholdBytes: Optional[int] = None
    
    # Trackers and web seeds
    announceTiers: List[List[str]] = []  # [[tier1_urls], [tier2_urls]]
    webSeeds: List[str] = []
    
    # Metadata
    comment: str = ""
    source: str = ""
    v2Mode: str = "v1"  # 'v1', 'v2', or 'hybrid'

class UserPreference(BaseModel):
    key: str
    value: Any
    user_id: str = "default"  # For multi-user support later

# =============================================================================
# SETTINGS MANAGEMENT API
# =============================================================================

@app.get("/api/settings")
async def get_settings():
    """Get current application settings (all layers merged)"""
    try:
        # Ensure managers are initialized
        if settings_storage is None or secure_config_manager is None:
            raise HTTPException(status_code=503, detail="Application not fully initialized")
            
        # Get effective settings (all layers merged)
        effective_settings = get_settings_storage().get_effective_settings()
        
        # Get layer information
        layer_info = get_settings_storage().get_layer_info()
        
        # Get credential status
        credential_status = get_secure_config_manager().get_credential_status()
        
        return {
            "settings": effective_settings,
            "layer_info": layer_info,
            "credentials_configured": credential_status
        }
        
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/layers")
async def get_settings_layers():
    """Get information about settings layers"""
    try:
        storage = get_settings_storage()
        return storage.get_layer_info()
    except Exception as e:
        logger.error(f"Error getting settings layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/{section}")
async def get_settings_section(section: str):
    """Get a specific settings section"""
    try:
        storage = get_settings_storage()
        section_settings = storage.get_section(section)
        return {"section": section, "settings": section_settings}
    except Exception as e:
        logger.error(f"Error getting settings section {section}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def update_settings(request: SettingsUpdateRequest):
    """Update application settings using multi-layer storage"""
    try:
        # Validate settings
        valid, message = SettingsValidator.validate_section(request.section, request.settings)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid settings: {message}")
        
        # Determine storage layer
        layer = "runtime" if not request.persist else "user"
        
        # Update settings
        success = get_settings_storage().update_section(
            section=request.section,
            settings=request.settings,
            layer=layer,
            persist=True
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")
        
        # Refresh torrent manager if qBittorrent settings changed
        if request.section == "qbittorrent":
            await refresh_torrent_manager()
        
        return {
            "success": True,
            "message": f"Settings updated in {layer} layer",
            "section": request.section,
            "layer": layer
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/reset")
async def reset_settings(section: Optional[str] = None, layer: str = "user"):
    """Reset settings to defaults"""
    try:
        if section:
            # Reset specific section
            success = get_settings_storage().reset_section(section, layer)
        else:
            # Reset all settings in layer
            success = get_settings_storage().reset_all(layer)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset settings")
        
        return {
            "success": True,
            "message": f"Settings reset {'for section ' + section if section else 'completely'} in {layer} layer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/apply-to-base")
async def apply_user_settings_to_base(section: Optional[str] = None):
    """Apply user settings to base config file (permanent change)"""
    try:
        success = get_settings_storage().apply_to_base_config(section)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to apply settings to base config")
        
        return {
            "success": True,
            "message": f"User settings {'for section ' + section if section else ''} applied to base config",
            "warning": "This permanently modifies config.yaml"
        }
        
    except Exception as e:
        logger.error(f"Error applying settings to base config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/validate")
async def validate_settings_section(section: str, settings: Dict[str, Any]):
    """Validate settings before applying"""
    try:
        valid, message = SettingsValidator.validate_section(section, settings)
        
        return {
            "valid": valid,
            "message": message,
            "section": section
        }
        
    except Exception as e:
        logger.error(f"Error validating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# CREDENTIAL MANAGEMENT API
# =============================================================================

@app.get("/api/credentials/status")
async def get_credential_status():
    """Get status of configured credentials"""
    try:
        return get_secure_config_manager().get_credential_status()
    except Exception as e:
        logger.error(f"Error getting credential status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/credentials")
async def store_credential(request: CredentialRequest):
    """Store a secure credential"""
    try:
        success = get_secure_config_manager().store_secure_value(request.key, request.value)
        
        if success:
            return {
                "success": True,
                "message": f"Credential '{request.key}' stored securely"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store credential")
            
    except Exception as e:
        logger.error(f"Error storing credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/credentials/{key}")
async def delete_credential(key: str):
    """Delete a stored credential"""
    try:
        credential_manager = CredentialManager()
        success = credential_manager.delete_credential(key)
        
        if success:
            return {
                "success": True,
                "message": f"Credential '{key}' deleted"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Credential '{key}' not found")
            
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# TORRENT MANAGEMENT API
# =============================================================================

@app.post("/api/torrent/create")
async def create_torrent(request: TorrentCreationRequest, background_tasks: BackgroundTasks):
    """Create a torrent (async operation)"""
    try:
        # Validate source path
        if not Path(request.source_path).exists():
            raise HTTPException(status_code=400, detail=f"Source path does not exist: {request.source_path}")
        
        # Generate proper task ID using UUID
        task_id = f"torrent_{uuid.uuid4().hex[:8]}"
        
        # Start torrent creation in background
        background_tasks.add_task(
            create_torrent_background,
            task_id,
            request
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Torrent creation started",
            "status_url": f"/api/torrent/status/{task_id}",
            "download_url": f"/api/torrent/download/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting torrent creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/torrent/status/{task_id}")
async def get_torrent_status(task_id: str):
    """Get torrent creation task status"""
    try:
        # Use TorrentManager's status tracking
        status = await get_torrent_manager().get_torrent_creation_status(task_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting torrent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/torrent/download/{task_id}")
async def download_torrent_file(task_id: str):
    """Download the created torrent file"""
    try:
        from fastapi.responses import Response
        
        # Get torrent file bytes from TorrentManager
        torrent_bytes = await get_torrent_manager().get_torrent_file_bytes(task_id)
        
        if torrent_bytes is None:
            raise HTTPException(status_code=404, detail=f"Torrent file for task {task_id} not found or not ready")
        
        # Return as downloadable file
        return Response(
            content=torrent_bytes,
            media_type="application/x-bittorrent",
            headers={"Content-Disposition": f"attachment; filename={task_id}.torrent"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading torrent file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qbittorrent/test")
async def test_qbittorrent_connection():
    """Test qBittorrent connection"""
    try:
        success, message = await get_torrent_manager().test_connection()
        
        return {
            "success": success,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error testing qBittorrent connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qbittorrent/info")
async def get_qbittorrent_info():
    """Get qBittorrent application information"""
    try:
        info = await get_torrent_manager().get_qbittorrent_info()
        return info
    except Exception as e:
        logger.error(f"Error getting qBittorrent info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# USER PREFERENCES API
# =============================================================================

@app.get("/api/preferences")
async def get_user_preferences(user_id: str = "default"):
    """Get user preferences (UI state, etc.)"""
    try:
        prefs_file = Path(f"config/user_preferences_{user_id}.json")
        
        if prefs_file.exists():
            import json
            with open(prefs_file, 'r') as f:
                return json.load(f)
        else:
            return {}
            
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences")
async def save_user_preference(request: UserPreference):
    """Save a user preference"""
    try:
        prefs_file = Path(f"config/user_preferences_{request.user_id}.json")
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing preferences
        preferences = {}
        if prefs_file.exists():
            import json
            with open(prefs_file, 'r') as f:
                preferences = json.load(f)
        
        # Update preference
        preferences[request.key] = request.value
        
        # Save back to file
        import json
        with open(prefs_file, 'w') as f:
            json.dump(preferences, f, indent=2)
        
        return {
            "success": True,
            "message": f"Preference '{request.key}' saved"
        }
        
    except Exception as e:
        logger.error(f"Error saving user preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def refresh_torrent_manager():
    """Refresh torrent manager with new settings"""
    global torrent_manager
    
    try:
        # Clean up existing manager
        if torrent_manager:
            await torrent_manager.cleanup()
        
        # Get effective settings and create config object
        effective_settings = get_settings_storage().get_effective_settings()
        config = AppConfig.from_dict(effective_settings)
        
        # Create new manager with updated config
        torrent_manager = TorrentManager(config, config_manager)
        
        logger.info("✅ Torrent manager refreshed with new settings")
        
    except Exception as e:
        logger.error(f"Error refreshing torrent manager: {e}")

async def create_torrent_background(task_id: str, request: TorrentCreationRequest):
    """Background task for torrent creation"""
    try:
        assert torrent_manager is not None
        result = await get_torrent_manager().create_torrent(
            source_path=request.source_path,
            private=request.private,
            start_seeding=request.start_seeding,
            format=request.format,
            piece_size=request.piece_size,
            comment=request.comment,
            trackers=request.trackers,
            url_seeds=request.url_seeds,
            source=request.source
        )
        
        # Store result somewhere (implement based on your needs)
        logger.info(f"Torrent creation completed for task {task_id}: {result}")
        
    except Exception as e:
        logger.error(f"Background torrent creation failed for task {task_id}: {e}")

# =============================================================================
# NEW API ENDPOINTS FOR WEB UI
# =============================================================================

@app.post("/api/scan", response_model=ScanResponse)
async def scan_path(request: ScanRequest):
    """Scan a file or folder path and return metadata"""
    ensure_managers_initialized()
    
    try:
        from src.utils.file_utils import get_folder_info, validate_folder_for_torrent
        
        path = Path(request.path)
        
        # Basic validation
        if not path.exists():
            return ScanResponse(
                totalBytes=0,
                fileCount=0,
                exists=False,
                mode="unknown",
                error="Path does not exist"
            )
        
        # Get folder info
        info = get_folder_info(path)
        
        if info.get("error"):
            return ScanResponse(
                totalBytes=0,
                fileCount=0,
                exists=True,
                mode="error",
                error=str(info["error"])
            )
        
        # Determine mode
        mode = "file" if info.get("is_file", False) else "folder"
        
        return ScanResponse(
            totalBytes=info["total_size"],
            fileCount=info["file_count"],
            exists=True,
            mode=mode
        )
        
    except Exception as e:
        logger.error(f"Error scanning path {request.path}: {e}")
        return ScanResponse(
            totalBytes=0,
            fileCount=0,
            exists=False,
            mode="error",
            error=str(e)
        )

@app.post("/api/pieces", response_model=PiecesResponse)
async def calculate_pieces(request: PiecesRequest):
    """Calculate optimal piece size and piece count"""
    try:
        total_bytes = request.totalBytes
        target_pieces = request.target or 2500
        
        if request.desiredPieceSize:
            # Manual piece size
            piece_size = request.desiredPieceSize
        else:
            # Auto piece size calculation (from spec)
            piece_size = 64 * 1024  # Start with 64 KiB
            max_piece_size = 16 * 1024 * 1024  # Max 16 MiB
            
            while (total_bytes / piece_size) > target_pieces and piece_size < max_piece_size:
                piece_size *= 2
        
        # Calculate piece count
        piece_count = math.ceil(total_bytes / piece_size)
        
        return PiecesResponse(
            pieceSizeBytes=piece_size,
            pieceCount=piece_count
        )
        
    except Exception as e:
        logger.error(f"Error calculating pieces: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Global storage for active jobs (in production, use Redis or database)
active_jobs: Dict[str, Dict[str, Any]] = {}

@app.post("/api/create-enhanced")
async def create_torrent_enhanced(request: CreateTorrentRequest, background_tasks: BackgroundTasks):
    """Enhanced torrent creation endpoint matching the spec"""
    ensure_managers_initialized()
    
    try:
        # Generate job ID
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        # Store job info
        active_jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "phase": "validation",
            "request": request.dict()
        }
        
        # Convert spec format to our backend format
        # Flatten announce tiers into a single list
        trackers = []
        for tier in request.announceTiers:
            trackers.extend(tier)
        
        # Create torrent using our existing backend
        background_tasks.add_task(
            create_torrent_background_enhanced,
            job_id,
            request.path,
            request.privateTorrent,
            request.startSeeding,
            request.comment,
            trackers,
            request.webSeeds,
            request.source,
            request.pieceSizeBytes,
            request.optimizeAlignment,
            request.alignThresholdBytes
        )
        
        return {
            "success": True,
            "jobId": job_id,
            "message": "Torrent creation started",
            "status_url": f"/api/create/stream?jobId={job_id}",
            "job_url": f"/api/create/status/{job_id}"
        }
        
    except Exception as e:
        logger.error(f"Error starting enhanced torrent creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/create/stream")
async def stream_torrent_progress(jobId: str):
    """Stream torrent creation progress via SSE"""
    
    async def event_stream():
        """Generate SSE events for torrent creation progress"""
        try:
            if jobId not in active_jobs:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return
            
            # Stream job progress
            last_status = None
            while jobId in active_jobs:
                job = active_jobs[jobId]
                status = job["status"]
                
                # Only send updates when status changes
                if status != last_status:
                    if status == "scanning":
                        yield f"event: scan\ndata: {json.dumps({'files': job.get('files', 0), 'bytes': job.get('bytes', 0)})}\n\n"
                    elif status == "hashing":
                        yield f"event: hash\ndata: {json.dumps({'progress': job.get('progress', 0), 'currentFile': job.get('currentFile', '')})}\n\n"
                    elif status == "finalizing":
                        yield f"event: finalize\ndata: {json.dumps({'pieceCount': job.get('pieceCount', 0)})}\n\n"
                    elif status == "completed":
                        yield f"event: done\ndata: {json.dumps(job.get('result', {}))}\n\n"
                        break
                    elif status == "error":
                        yield f"event: error\ndata: {json.dumps({'message': job.get('error', 'Unknown error')})}\n\n"
                        break
                    
                    last_status = status
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/api/create/status/{job_id}")
async def get_job_status(job_id: str):
    """Get current status of a torrent creation job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return active_jobs[job_id]

async def create_torrent_background_enhanced(
    job_id: str,
    source_path: str,
    private: bool,
    start_seeding: bool,
    comment: str,
    trackers: List[str],
    url_seeds: List[str],
    source: str,
    piece_size: Optional[int],
    optimize_alignment: bool,
    align_threshold: Optional[int]
):
    """Enhanced background task for torrent creation with progress tracking"""
    try:
        # Update job status
        active_jobs[job_id]["status"] = "scanning"
        active_jobs[job_id]["phase"] = "scanning"
        
        # Use our existing torrent manager
        assert torrent_manager is not None
        
        result = await get_torrent_manager().create_torrent(
            source_path=source_path,
            private=private,
            start_seeding=start_seeding,
            comment=comment,
            trackers=trackers,
            url_seeds=url_seeds,
            source=source,
            piece_size=piece_size,
            optimize_alignment=optimize_alignment,
            padded_file_size_limit=align_threshold
        )
        
        # Update job with completion
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["result"] = result
        
        # Clean up job after 5 minutes
        await asyncio.sleep(300)
        if job_id in active_jobs:
            del active_jobs[job_id]
        
    except Exception as e:
        logger.error(f"Enhanced background torrent creation failed for job {job_id}: {e}")
        active_jobs[job_id]["status"] = "error"
        active_jobs[job_id]["error"] = str(e)

# =============================================================================
# NEW QBITTORRENT BROWSING API
# =============================================================================

@app.post("/api/qbittorrent/browse")
async def browse_qbittorrent_directory(request: dict):
    """Browse directories using qBittorrent API"""
    try:
        ensure_managers_initialized()
        
        path = request.get("path", "/")
        result = await get_torrent_manager().browse_qbittorrent_directory(path)
        
        return result
        
    except Exception as e:
        logger.error(f"Error browsing qBittorrent directory {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qbittorrent/scan")
async def scan_qbittorrent_path(request: dict):
    """Scan a path using qBittorrent API"""
    try:
        ensure_managers_initialized()
        
        path = request.get("path", "/")
        result = await get_torrent_manager().scan_qbittorrent_path(path)
        
        return result
        
    except Exception as e:
        logger.error(f"Error scanning qBittorrent path {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qbittorrent/default-paths")
async def get_qbittorrent_default_paths():
    """Get default paths available in qBittorrent"""
    try:
        ensure_managers_initialized()
        
        paths = await get_torrent_manager().get_qbittorrent_default_paths()
        
        return {
            "success": True,
            "paths": paths,
            "navigation_mode": "qbittorrent"
        }
        
    except Exception as e:
        logger.error(f"Error getting qBittorrent default paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qbittorrent/analyze")
async def analyze_qbittorrent_path(request: dict):
    """Deep analysis of a path with recursive size calculation"""
    path = request.get("path", "/")  # Define path early for error handling
    try:
        ensure_managers_initialized()
        
        include_size = request.get("includeSize", True)
        recursive = request.get("recursive", True)
        
        result = await get_torrent_manager().analyze_qbittorrent_path(
            path=path, 
            include_size=include_size, 
            recursive=recursive
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing qBittorrent path {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qbittorrent/calculate-pieces")
async def calculate_optimal_piece_size(request: dict):
    """Calculate optimal piece size for a given path using intelligent algorithms"""
    path = request.get("path", "/")
    try:
        ensure_managers_initialized()
        
        target_pieces = request.get("targetPieces", 2500)
        
        result = await get_torrent_manager().calculate_optimal_piece_size(
            path=path,
            target_pieces=target_pieces
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating piece size for path {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/unified/browse")
async def unified_browse_directory(request: dict):
    """Unified directory browsing (supports both local and qBittorrent modes)"""
    try:
        ensure_managers_initialized()
        
        path = request.get("path", "/")
        mode = request.get("mode", "qbittorrent")  # Default to qBittorrent mode
        
        if mode == "qbittorrent":
            # Use qBittorrent API browsing
            result = await get_torrent_manager().browse_qbittorrent_directory(path)
            return result
        else:
            # Use legacy local filesystem browsing (placeholder)
            return {
                "success": False,
                "error": "Local browsing mode not yet implemented in unified API",
                "current_path": path,
                "entries": [],
                "navigation_mode": "local"
            }
        
    except Exception as e:
        logger.error(f"Error in unified browse for path {path} with mode {mode}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/unified/scan")
async def unified_scan_path(request: dict):
    """Unified path scanning (supports both local and qBittorrent modes)"""
    try:
        ensure_managers_initialized()
        
        path = request.get("path", "/")
        mode = request.get("mode", "qbittorrent")  # Default to qBittorrent mode
        
        if mode == "qbittorrent":
            # Use qBittorrent API scanning
            result = await get_torrent_manager().scan_qbittorrent_path(path)
            return result
        else:
            # Use legacy local filesystem scanning
            # Use existing local scanning logic
            from src.utils.file_utils import get_folder_info, validate_folder_for_torrent
            
            path_obj = Path(path)
            
            # Basic validation
            if not path_obj.exists():
                return {
                    "success": True,
                    "path": path,
                    "exists": False,
                    "is_directory": False,
                    "file_count": 0,
                    "total_bytes": 0,
                    "navigation_mode": "local",
                    "error": "Path does not exist"
                }
            
            # Get folder info
            info = get_folder_info(path_obj)
            
            if info.get("error"):
                return {
                    "success": True,
                    "path": path,
                    "exists": True,
                    "is_directory": False,
                    "file_count": 0,
                    "total_bytes": 0,
                    "navigation_mode": "local",
                    "error": str(info["error"])
                }
            
            return {
                "success": True,
                "path": path,
                "exists": True,
                "is_directory": not info.get("is_file", False),
                "file_count": info["file_count"],
                "total_bytes": info["total_size"],
                "navigation_mode": "local"
            }
        
    except Exception as e:
        logger.error(f"Error in unified scan for path {path} with mode {mode}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# WEB UI ROUTES
# =============================================================================

@app.get("/")
async def root(request: Request):
    """Serve the main torrent creator UI"""
    return templates.TemplateResponse("torrent_creator.html", {"request": request})

@app.get("/creator")
async def torrent_creator_ui(request: Request):
    """Serve the torrent creator UI (alternative route)"""
    return templates.TemplateResponse("torrent_creator.html", {"request": request})

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "managers": {
            "config_manager": config_manager is not None,
            "secure_config_manager": secure_config_manager is not None,
            "torrent_manager": torrent_manager is not None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8094)
