"""
FastAPI web application for Easy Torrent Creator
"""
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..core.config_manager import ConfigManager
from ..core.torrent_manager import TorrentManager


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
    default_output_dir: str
    torrent_creation: dict
    trackers: List[str]


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# Web routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "Easy Torrent Creator"
    })


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    return templates.TemplateResponse("config.html", {
        "request": request,
        "page_title": "Configuration - Easy Torrent Creator"
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
async def test_connection():
    """Test connection to qBittorrent"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        manager = TorrentManager(config)
        success = await manager.test_connection()
        return {
            "success": success,
            "message": "Connection successful!" if success else "Connection failed - check settings"
        }
    except Exception as e:
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
        
        # Update configuration
        config = config_manager.get_config()
        config.update({
            "qbittorrent": request.qbittorrent,
            "default_output_dir": request.default_output_dir,
            "torrent_creation": request.torrent_creation,
            "trackers": request.trackers
        })
        
        # Save to file
        config_manager.save_config(config)
        
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        return {"success": False, "message": f"Failed to save configuration: {str(e)}"}


@app.get("/api/env-vars")
async def get_env_vars():
    """Get status of important environment variables"""
    env_vars = {
        'TRACKER': bool(os.getenv('TRACKER')),
        'QB_PASSWORD': bool(os.getenv('QB_PASSWORD')),
    }
    return env_vars


# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
