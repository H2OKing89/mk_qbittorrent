"""
FastAPI web application for Easy Torrent Creator
"""
import os
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..core.config_manager import ConfigManager
from ..core.torrent_manager import TorrentManager
from ..utils.docker_path_mapper import DockerPathMapper
from ..utils.credential_manager import CredentialManager, SecureConfigManager

# Configure logging
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(title="Easy Torrent Creator", description="Web interface for creating torrents with qBittorrent")

# Templates and static files
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


# Request/Response models
class FolderItem(BaseModel):
    name: str
    path: str
    type: str  # 'file', 'directory', 'parent'
    size: Optional[int] = None


class FolderListResponse(BaseModel):
    items: List[FolderItem]
    current_path: str


class FolderInfoResponse(BaseModel):
    name: str
    path: str
    size: int
    size_formatted: str
    file_count: int
    folder_count: int
    is_valid: bool
    validation_message: str


class CreateTorrentRequest(BaseModel):
    source_path: str
    output_dir: str
    private: bool = True
    start_seeding: bool = False


class SaveConfigRequest(BaseModel):
    qbittorrent: dict
    torrent_creation: dict
    web_server: Optional[dict] = None
    default_output_dir: str
    default_upload_root: str
    remember_last_folder: Optional[bool] = True
    auto_open_output_folder: Optional[bool] = True
    docker_mapping: Optional[dict] = None
    trackers: Optional[List[str]] = None


class CredentialRequest(BaseModel):
    key: str
    value: str
    customName: Optional[str] = None


class CredentialDeleteRequest(BaseModel):
    key: str


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_float = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} PB"


# Web routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - clean version with separated CSS/JS"""
    return templates.TemplateResponse("index_clean.html", {
        "request": request,
        "page_title": "Easy Torrent Creator"
    })


@app.get("/old", response_class=HTMLResponse)
async def home_old(request: Request):
    """Home page - original version with inline CSS/JS"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "Easy Torrent Creator (Original)"
    })


@app.get("/config-fixed", response_class=HTMLResponse)
async def config_fixed(request: Request):
    """Configuration page with improved credential management"""
    return templates.TemplateResponse("config_fixed.html", {
        "request": request,
        "page_title": "Easy Torrent Creator - Configuration (Fixed)"
    })


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    return templates.TemplateResponse("config.html", {
        "request": request,
        "page_title": "Configuration - Easy Torrent Creator"
    })


@app.get("/qbit", response_class=HTMLResponse)
async def qbit_style_home(request: Request):
    """qBittorrent-styled interface"""
    return templates.TemplateResponse("index_qbit_style.html", {
        "request": request,
        "page_title": "Easy Torrent Creator - qBittorrent Style"
    })


# API routes
@app.get("/api/folders")
async def list_folders(path: str = "/") -> FolderListResponse:
    """List folders and files in a directory"""
    try:
        folder_path = Path(path).resolve()
        
        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        items = []
        
        # Add parent directory if not at root
        if folder_path != folder_path.parent:
            items.append(FolderItem(
                name=".. (Parent)",
                path=str(folder_path.parent),
                type="parent"
            ))
        
        # List directory contents
        try:
            for item in sorted(folder_path.iterdir()):
                if item.is_dir():
                    items.append(FolderItem(
                        name=item.name,
                        path=str(item),
                        type="directory"
                    ))
                elif item.is_file():
                    try:
                        size = item.stat().st_size
                    except (OSError, PermissionError):
                        size = 0
                    
                    items.append(FolderItem(
                        name=item.name,
                        path=str(item),
                        type="file",
                        size=size
                    ))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        return FolderListResponse(items=items, current_path=str(folder_path))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/folder-info")
async def get_folder_info(path: str) -> FolderInfoResponse:
    """Get detailed information about a folder"""
    try:
        folder_path = Path(path)
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail="Path does not exist")
        
        # If path is a file, use its parent directory
        if folder_path.is_file():
            folder_path = folder_path.parent
        
        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        # Calculate folder statistics
        total_size = 0
        file_count = 0
        folder_count = 0
        
        try:
            for item in folder_path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    folder_count += 1
        except PermissionError:
            pass
        
        # Validation
        is_valid = True
        validation_message = "Folder is ready for torrent creation"
        
        if file_count == 0:
            is_valid = False
            validation_message = "Folder is empty"
        elif total_size == 0:
            is_valid = False
            validation_message = "No files with content found"
        elif total_size > 100 * 1024 * 1024 * 1024:  # 100GB
            validation_message = "Large folder - creation may take time"
        
        return FolderInfoResponse(
            name=folder_path.name,
            path=str(folder_path),
            size=total_size,
            size_formatted=format_file_size(total_size),
            file_count=file_count,
            folder_count=folder_count,
            is_valid=is_valid,
            validation_message=validation_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create-torrent")
async def create_torrent(request: CreateTorrentRequest):
    """Create a torrent file"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        manager = TorrentManager(config)
        
        # Validate source path
        source_path = Path(request.source_path)
        if not source_path.exists():
            return {"success": False, "error": "Source path does not exist"}
        
        # Create output directory if it doesn't exist
        output_path = Path(request.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create torrent
        result = await manager.create_torrent(
            source_path=str(source_path),
            output_dir=str(output_path),
            private=request.private,
            start_seeding=request.start_seeding
        )
        
        return result
    except Exception as e:
        return {"success": False, "error": f"Failed to create torrent: {str(e)}"}


@app.post("/api/test-connection")
async def test_connection(request: SaveConfigRequest):
    """Test connection to qBittorrent with provided config"""
    try:
        # Convert the request data to a config format
        config_dict = request.dict()
        
        # Create a temporary AppConfig object from the dictionary data
        from ..core.config_manager import AppConfig
        temp_config = AppConfig.from_dict(config_dict)
        
        # Create TorrentManager with the temporary config
        manager = TorrentManager(temp_config)
        success, message = await manager.test_connection()
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save-config")
async def save_config(request: SaveConfigRequest):
    """Save configuration"""
    try:
        config_manager = ConfigManager()
        
        # Convert the request data to a dictionary format
        config_dict = request.dict()
        
        # Create a new AppConfig object from the dictionary data
        from ..core.config_manager import AppConfig
        new_config = AppConfig.from_dict(config_dict)
        
        # Update the config manager's config and save it
        config_manager.config = new_config
        config_manager.save_config()
        
        logger.info("Configuration saved successfully")
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save configuration: {str(e)}")
        return {"success": False, "message": f"Failed to save configuration: {str(e)}"}


@app.get("/api/docker-mapping")
async def get_docker_mapping():
    """Get docker path mapping information"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Access docker mapping from config
        if hasattr(config, 'qbittorrent') and hasattr(config.qbittorrent, 'docker_path_mapping'):
            docker_mapping = config.qbittorrent.docker_path_mapping or {}
        else:
            docker_mapping = {}
        
        path_mapper = DockerPathMapper(docker_mapping)
        validation = path_mapper.validate_mapping()
        
        return {
            "mappings": docker_mapping,
            "mapped_roots": [str(root) for root in path_mapper.get_mapped_roots()],
            "validation": validation,
            "enabled": len(docker_mapping) > 0
        }
    except Exception as e:
        return {
            "mappings": {},
            "mapped_roots": [],
            "validation": {"is_valid": True, "issues": [], "warnings": []},
            "enabled": False,
            "error": str(e)
        }


@app.get("/api/env-vars")
async def get_env_vars():
    """Get status of important environment variables"""
    credential_manager = CredentialManager()
    status = {
        'TRACKER': credential_manager.has_credential('TRACKER'),
        'QBIT_PASSWORD': credential_manager.has_credential('QBIT_PASSWORD'),
    }
    return status


@app.post("/api/credentials")
async def store_credential(request: CredentialRequest):
    """Store a secure credential"""
    try:
        credential_manager = CredentialManager()
        success = credential_manager.store_credential(
            request.key, 
            request.value, 
            request.customName
        )
        
        if success:
            return {"success": True, "message": f"Credential '{request.key}' stored securely"}
        else:
            return {"success": False, "message": "Failed to store credential"}
    except Exception as e:
        return {"success": False, "message": f"Error storing credential: {str(e)}"}


@app.get("/api/credentials/details")
async def get_credential_details():
    """Get detailed credential information including masked values"""
    try:
        credential_manager = CredentialManager()
        return credential_manager.get_credential_details()
    except Exception as e:
        return {"error": f"Error getting credential details: {str(e)}"}


@app.delete("/api/credentials")
async def delete_credential(request: CredentialDeleteRequest):
    """Delete a credential"""
    try:
        credential_manager = CredentialManager()
        success = credential_manager.delete_credential(request.key)
        
        if success:
            return {"success": True, "message": f"Credential '{request.key}' deleted"}
        else:
            return {"success": False, "message": "Failed to delete credential"}
    except Exception as e:
        return {"success": False, "message": f"Error deleting credential: {str(e)}"}


@app.get("/api/credentials/status")
async def get_credential_status():
    """Get status of all important credentials"""
    try:
        secure_config = SecureConfigManager()
        return secure_config.get_credential_status()
    except Exception as e:
        return {"error": f"Error getting credential status: {str(e)}"}


@app.post("/api/migrate-env")
async def migrate_env_credentials():
    """Migrate credentials from .env file to secure storage"""
    try:
        credential_manager = CredentialManager()
        success = credential_manager.migrate_from_env()
        
        if success:
            return {"success": True, "message": "Credentials migrated to secure storage"}
        else:
            return {"success": False, "message": "Migration failed"}
    except Exception as e:
        return {"success": False, "message": f"Migration error: {str(e)}"}


# Run the app
if __name__ == "__main__":
    import uvicorn
    config_manager = ConfigManager()
    config = config_manager.get_config()
    uvicorn.run(
        "app:app", 
        host=config.web_server.host, 
        port=config.web_server.port, 
        reload=config.web_server.reload
    )
