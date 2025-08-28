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

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our application modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.config_manager import ConfigManager, AppConfig
from src.core.torrent_manager import TorrentManager
from src.utils.credential_manager import CredentialManager, SecureConfigManager
from src.utils.settings_storage import SettingsStorageManager, SettingsValidator

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
    if any(manager is None for manager in [config_manager, secure_config_manager, torrent_manager, settings_storage]):
        raise HTTPException(status_code=503, detail="Application managers not initialized")

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
    output_dir: Optional[str] = None
    private: Optional[bool] = None
    start_seeding: Optional[bool] = None
    format: Optional[str] = None
    piece_size: Optional[int] = None
    comment: Optional[str] = None
    trackers: Optional[List[str]] = None
    url_seeds: Optional[List[str]] = None
    source: Optional[str] = None

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
        effective_settings = settings_storage.get_effective_settings()
        
        # Get layer information
        layer_info = settings_storage.get_layer_info()
        
        # Get credential status
        credential_status = secure_config_manager.get_credential_status()
        
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
        return settings_storage.get_layer_info()
    except Exception as e:
        logger.error(f"Error getting settings layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/{section}")
async def get_settings_section(section: str):
    """Get specific settings section with all layers applied"""
    try:
        section_settings = settings_storage.get_section(section)
        
        if not section_settings:
            raise HTTPException(status_code=404, detail=f"Section '{section}' not found")
        
        return {
            "section": section,
            "settings": section_settings
        }
            
    except HTTPException:
        raise
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
        success = settings_storage.update_section(
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
            success = settings_storage.reset_section(section, layer)
        else:
            # Reset all settings in layer
            success = settings_storage.reset_all(layer)
        
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
        success = settings_storage.apply_to_base_config(section)
        
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
        return secure_config_manager.get_credential_status()
    except Exception as e:
        logger.error(f"Error getting credential status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/credentials")
async def store_credential(request: CredentialRequest):
    """Store a secure credential"""
    try:
        success = secure_config_manager.store_secure_value(request.key, request.value)
        
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
        status = await torrent_manager.get_torrent_creation_status(task_id)
        
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
        torrent_bytes = await torrent_manager.get_torrent_file_bytes(task_id)
        
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
        success, message = await torrent_manager.test_connection()
        
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
        info = await torrent_manager.get_qbittorrent_info()
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
        effective_settings = settings_storage.get_effective_settings()
        config = AppConfig.from_dict(effective_settings)
        
        # Create new manager with updated config
        torrent_manager = TorrentManager(config, config_manager)
        
        logger.info("✅ Torrent manager refreshed with new settings")
        
    except Exception as e:
        logger.error(f"Error refreshing torrent manager: {e}")

async def create_torrent_background(task_id: str, request: TorrentCreationRequest):
    """Background task for torrent creation"""
    try:
        result = await torrent_manager.create_torrent(
            source_path=request.source_path,
            output_dir=request.output_dir,
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
