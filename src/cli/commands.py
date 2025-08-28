"""
Command Line Interface for Easy Torrent Creator
"""
import asyncio
from pathlib import Path
from typing import Optional

from ..core.config_manager import ConfigManager
from ..core.torrent_manager import TorrentManager
from ..utils.file_utils import validate_folder_for_torrent, format_file_size, get_folder_info


class CLIHandler:
    """Handles command line operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.torrent_manager = None
    
    async def create_torrent(
        self,
        source_path: str,
        output_dir: Optional[str] = None,
        private: bool = True,
        start_seeding: bool = False
    ):
        """
        Create torrent from command line
        
        Args:
            source_path: Path to folder/file to create torrent from
            output_dir: Output directory (uses config default if None)
            private: Whether to create private torrent
            start_seeding: Whether to start seeding immediately
        """
        try:
            # Validate source path
            source = Path(source_path)
            if not source.exists():
                print(f"❌ Error: Source path does not exist: {source_path}")
                return
            
            # Validate source for torrent creation
            is_valid, message = validate_folder_for_torrent(source)
            if not is_valid:
                print(f"❌ Error: {message}")
                return
            
            # Show validation message if it's a warning
            if "Large folder" in message:
                print(f"⚠️  Warning: {message}")
            
            # Get folder info
            info = get_folder_info(source)
            print(f"📁 Source: {info['name']}")
            print(f"📊 Size: {format_file_size(info['total_size'])}")
            print(f"📄 Files: {info['file_count']} files in {info['folder_count']} folders")
            print()
            
            # Determine output directory
            if output_dir is None:
                config = self.config_manager.get_config()
                output_dir = config.default_output_dir
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            print(f"💾 Output directory: {output_dir}")
            print(f"🔒 Private torrent: {'Yes' if private else 'No'}")
            print(f"🌱 Start seeding: {'Yes' if start_seeding else 'No'}")
            print()
            
            # Test qBittorrent connection first
            print("🔌 Testing qBittorrent connection...")
            config = self.config_manager.get_config()
            self.torrent_manager = TorrentManager(config, self.config_manager)
            
            success, message = await self.torrent_manager.test_connection()
            if not success:
                print(f"❌ qBittorrent connection failed: {message}")
                print("💡 Please check your qBittorrent configuration and ensure it's running")
                return
            
            print(f"✅ {message}")
            print()
            
            # Create torrent
            print("🚀 Creating torrent...")
            result = await self.torrent_manager.create_torrent(
                source_path=source_path,
                output_dir=output_dir,
                private=private,
                start_seeding=start_seeding
            )
            
            if result["success"]:
                print("✅ Torrent created successfully!")
                print()
                
                if result.get("torrent_path"):
                    print(f"💾 Torrent file: {result['torrent_path']}")
                
                if result.get("torrent_hash"):
                    print(f"🔑 Hash: {result['torrent_hash']}")
                
                if start_seeding and result.get("torrent_hash"):
                    print("🌱 Torrent has been added to qBittorrent for seeding")
                
            else:
                print("❌ Torrent creation failed!")
                error = result.get("error", "Unknown error")
                print(f"💥 Error: {error}")
                
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            if self.torrent_manager:
                await self.torrent_manager.disconnect()


def print_cli_help():
    """Print CLI help information"""
    help_text = """
📦 Easy Torrent Creator - CLI Mode

Usage:
  python main.py --cli /path/to/folder [options]

Options:
  --output DIR         Output directory for torrent file
  --private           Create private torrent (default)
  --start-seeding     Start seeding after creation
  --config-file FILE  Configuration file path
  --verbose           Enable verbose logging

Examples:
  # Create torrent from a folder
  python main.py --cli /home/user/MyFolder

  # Create torrent with custom output directory
  python main.py --cli /home/user/MyFolder --output /home/user/torrents

  # Create public torrent and start seeding
  python main.py --cli /home/user/MyFolder --start-seeding

Configuration:
  The application uses config/config.yaml for qBittorrent settings.
  Make sure to configure your qBittorrent connection details first.

GUI Mode:
  Run without --cli to use the graphical interface:
  python main.py
    """
    print(help_text)
