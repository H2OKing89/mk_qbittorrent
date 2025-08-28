"""
Main GUI Window for Easy Torrent Creator
Provides an intuitive interface for torrent creation
"""
import asyncio
import sys
import threading
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

from ..core.config_manager import ConfigManager, ConfigError
from ..core.torrent_manager import TorrentManager
from ..utils.file_utils import format_file_size, get_folder_info


class TorrentCreatorApp:
    """Main application window for torrent creation"""
    
    def __init__(self, config_manager: ConfigManager):
        if not HAS_TKINTER:
            raise RuntimeError("tkinter is required for GUI mode. Please install tkinter or use CLI mode.")
        
        self.config_manager = config_manager
        self.torrent_manager = None
        self.root = None
        self.current_folder = None
        
        # UI Components
        self.folder_var = None
        self.status_var = None
        self.progress_var = None
        self.folder_info_frame = None
        
    async def run(self):
        """Run the GUI application"""
        # Create the GUI in a separate thread to handle async operations
        def run_gui():
            self.root = tk.Tk()
            self.setup_ui()
            self.root.mainloop()
        
        # Start GUI in main thread (required for tkinter)
        self.root = tk.Tk()
        self.setup_ui()
        
        # Handle the event loop integration
        try:
            await self.async_mainloop()
        except KeyboardInterrupt:
            if self.root:
                self.root.quit()
    
    async def async_mainloop(self):
        """Async-compatible mainloop"""
        while True:
            try:
                if not self.root or not self.root.winfo_exists():
                    break
                self.root.update()
                await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
            except tk.TclError:
                break  # Window was destroyed
    
    def setup_ui(self):
        """Setup the user interface"""
        self.root.title("Easy Torrent Creator")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        try:
            style.theme_use('clam')  # Modern looking theme
        except:
            pass  # Use default theme if clam not available
        
        # Variables
        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar()
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        self.create_header(main_frame)
        self.create_folder_selection(main_frame)
        self.create_folder_info(main_frame)
        self.create_options(main_frame)
        self.create_action_buttons(main_frame)
        self.create_status_section(main_frame)
        
        # Load last folder if enabled
        self.load_last_folder()
    
    def create_header(self, parent):
        """Create header section"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = ttk.Label(
            header_frame, 
            text="Easy Torrent Creator",
            font=("TkDefaultFont", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Create torrents easily with qBittorrent integration",
            font=("TkDefaultFont", 10)
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Config button
        config_btn = ttk.Button(
            header_frame,
            text="⚙️ Settings",
            command=self.open_settings
        )
        config_btn.grid(row=0, column=1, sticky=tk.E)
    
    def create_folder_selection(self, parent):
        """Create folder selection section"""
        folder_frame = ttk.LabelFrame(parent, text="Select Folder to Share", padding="10")
        folder_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        folder_frame.columnconfigure(1, weight=1)
        
        # Folder path entry
        ttk.Label(folder_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state="readonly")
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_btn = ttk.Button(
            folder_frame,
            text="📁 Browse",
            command=self.browse_folder
        )
        browse_btn.grid(row=0, column=2, sticky=tk.E)
        
        # Quick access buttons for common locations
        quick_frame = ttk.Frame(folder_frame)
        quick_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(quick_frame, text="Quick access:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        home_btn = ttk.Button(
            quick_frame,
            text="🏠 Home",
            command=lambda: self.set_quick_folder(Path.home())
        )
        home_btn.grid(row=0, column=1, padx=(0, 5))
        
        desktop_btn = ttk.Button(
            quick_frame,
            text="🖥️ Desktop", 
            command=lambda: self.set_quick_folder(Path.home() / "Desktop")
        )
        desktop_btn.grid(row=0, column=2, padx=(0, 5))
        
        downloads_btn = ttk.Button(
            quick_frame,
            text="📥 Downloads",
            command=lambda: self.set_quick_folder(Path.home() / "Downloads")
        )
        downloads_btn.grid(row=0, column=3, padx=(0, 5))
    
    def create_folder_info(self, parent):
        """Create folder information display"""
        self.folder_info_frame = ttk.LabelFrame(parent, text="Folder Information", padding="10")
        self.folder_info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Initially hidden
        self.folder_info_frame.grid_remove()
    
    def create_options(self, parent):
        """Create torrent options section"""
        options_frame = ttk.LabelFrame(parent, text="Torrent Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        options_frame.columnconfigure(1, weight=1)
        
        # Private torrent option
        self.private_var = tk.BooleanVar(value=True)
        private_check = ttk.Checkbutton(
            options_frame,
            text="Private torrent",
            variable=self.private_var
        )
        private_check.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Start seeding option
        self.start_seeding_var = tk.BooleanVar(value=False)
        seeding_check = ttk.Checkbutton(
            options_frame,
            text="Start seeding immediately",
            variable=self.start_seeding_var
        )
        seeding_check.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Auto-open output folder
        self.auto_open_var = tk.BooleanVar(value=True)
        auto_open_check = ttk.Checkbutton(
            options_frame,
            text="Open output folder when done",
            variable=self.auto_open_var
        )
        auto_open_check.grid(row=2, column=0, sticky=tk.W)
        
        # Output directory selection
        ttk.Label(options_frame, text="Save torrent to:").grid(row=0, column=1, sticky=tk.W, padx=(20, 10))
        
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(options_frame, textvariable=self.output_var, width=40)
        output_entry.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(0, 10))
        
        output_browse_btn = ttk.Button(
            options_frame,
            text="📁",
            command=self.browse_output_folder,
            width=3
        )
        output_browse_btn.grid(row=0, column=3)
        
        # Load default output directory
        config = self.config_manager.get_config()
        self.output_var.set(config.default_output_dir)
    
    def create_action_buttons(self, parent):
        """Create main action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(0, 15))
        
        # Create torrent button
        self.create_btn = ttk.Button(
            button_frame,
            text="🚀 Create Torrent",
            command=self.create_torrent,
            style="Accent.TButton"
        )
        self.create_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Test connection button  
        test_btn = ttk.Button(
            button_frame,
            text="🔗 Test qBittorrent Connection",
            command=self.test_connection
        )
        test_btn.grid(row=0, column=1)
        
        # Initially disable create button
        self.create_btn.configure(state="disabled")
    
    def create_status_section(self, parent):
        """Create status and progress section"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="10")
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.S))
        status_frame.columnconfigure(0, weight=1)
        
        # Status label
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            mode='determinate'
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def browse_folder(self):
        """Open folder browser dialog"""
        initial_dir = self.folder_var.get() or self.config_manager.get_last_folder() or str(Path.home())
        
        folder = filedialog.askdirectory(
            title="Select folder to create torrent from",
            initialdir=initial_dir
        )
        
        if folder:
            self.set_folder(folder)
    
    def set_quick_folder(self, folder_path: Path):
        """Set folder from quick access button"""
        if folder_path.exists() and folder_path.is_dir():
            self.set_folder(str(folder_path))
        else:
            messagebox.showwarning("Folder Not Found", f"Folder not found: {folder_path}")
    
    def set_folder(self, folder_path: str):
        """Set the selected folder and update UI"""
        self.folder_var.set(folder_path)
        self.current_folder = Path(folder_path)
        
        # Save last folder
        self.config_manager.save_last_folder(folder_path)
        
        # Update folder info
        self.update_folder_info()
        
        # Enable create button
        self.create_btn.configure(state="normal")
        
        self.status_var.set(f"Selected: {self.current_folder.name}")
    
    def update_folder_info(self):
        """Update folder information display"""
        if not self.current_folder or not self.current_folder.exists():
            self.folder_info_frame.grid_remove()
            return
        
        # Get folder information
        folder_info = get_folder_info(self.current_folder)
        
        # Clear existing info
        for widget in self.folder_info_frame.winfo_children():
            widget.destroy()
        
        # Display info
        info_text = f"""
Name: {folder_info['name']}
Size: {format_file_size(folder_info['total_size'])}
Files: {folder_info['file_count']} files in {folder_info['folder_count']} folders
Path: {folder_info['path']}
        """.strip()
        
        info_label = ttk.Label(self.folder_info_frame, text=info_text, justify=tk.LEFT)
        info_label.grid(row=0, column=0, sticky=tk.W)
        
        # Show the frame
        self.folder_info_frame.grid()
    
    def browse_output_folder(self):
        """Browse for output folder"""
        initial_dir = self.output_var.get() or str(Path.home())
        
        folder = filedialog.askdirectory(
            title="Select output folder for torrent files",
            initialdir=initial_dir
        )
        
        if folder:
            self.output_var.set(folder)
    
    def load_last_folder(self):
        """Load the last used folder if available"""
        last_folder = self.config_manager.get_last_folder()
        if last_folder and Path(last_folder).exists():
            self.set_folder(last_folder)
    
    def open_settings(self):
        """Open settings window"""
        try:
            from .config_window import ConfigWindow
            config_window = ConfigWindow(self.config_manager, self.root)
            config_window.show()
        except ImportError:
            messagebox.showerror("Error", "Settings window not available")
    
    def test_connection(self):
        """Test qBittorrent connection"""
        def test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._test_connection_async())
                self.root.after(0, lambda: self._show_connection_result(result))
            finally:
                loop.close()
        
        # Run test in background thread
        self.status_var.set("Testing qBittorrent connection...")
        self.progress_bar.configure(mode='indeterminate')
        self.progress_bar.start()
        
        threading.Thread(target=test_async, daemon=True).start()
    
    async def _test_connection_async(self):
        """Async connection test"""
        try:
            if not self.torrent_manager:
                config = self.config_manager.get_config()
                self.torrent_manager = TorrentManager(config, self.config_manager)
            
            success, message = await self.torrent_manager.test_connection()
            return success, message
        except Exception as e:
            return False, str(e)
    
    def _show_connection_result(self, result):
        """Show connection test result"""
        self.progress_bar.stop()
        self.progress_bar.configure(mode='determinate')
        
        success, message = result
        if success:
            self.status_var.set("✅ qBittorrent connection successful")
            messagebox.showinfo("Connection Test", f"✅ Success!\n\n{message}")
        else:
            self.status_var.set("❌ qBittorrent connection failed")
            messagebox.showerror("Connection Test", f"❌ Failed!\n\n{message}")
    
    def create_torrent(self):
        """Create torrent from selected folder"""
        if not self.current_folder or not self.current_folder.exists():
            messagebox.showerror("Error", "Please select a valid folder first")
            return
        
        # Validate output directory
        output_dir = self.output_var.get()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return
        
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output directory: {e}")
            return
        
        def create_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._create_torrent_async())
                self.root.after(0, lambda: self._show_creation_result(result))
            finally:
                loop.close()
        
        # Disable create button and start progress
        self.create_btn.configure(state="disabled")
        self.status_var.set("Creating torrent...")
        self.progress_bar.configure(mode='indeterminate')
        self.progress_bar.start()
        
        threading.Thread(target=create_async, daemon=True).start()
    
    async def _create_torrent_async(self):
        """Async torrent creation"""
        try:
            if not self.torrent_manager:
                config = self.config_manager.get_config()
                self.torrent_manager = TorrentManager(config, self.config_manager)
            
            # Create torrent
            result = await self.torrent_manager.create_torrent(
                source_path=str(self.current_folder),
                output_dir=self.output_var.get(),
                private=self.private_var.get(),
                start_seeding=self.start_seeding_var.get()
            )
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _show_creation_result(self, result):
        """Show torrent creation result"""
        self.progress_bar.stop()
        self.progress_bar.configure(mode='determinate')
        self.create_btn.configure(state="normal")
        
        if result["success"]:
            self.status_var.set("✅ Torrent created successfully!")
            
            message = "✅ Torrent created successfully!"
            if result.get("torrent_path"):
                message += f"\n\nSaved to: {result['torrent_path']}"
            if result.get("torrent_hash"):
                message += f"\nHash: {result['torrent_hash'][:16]}..."
            
            messagebox.showinfo("Success", message)
            
            # Auto-open output folder if enabled
            if self.auto_open_var.get():
                self.open_output_folder()
        else:
            error_msg = result.get("error", "Unknown error")
            self.status_var.set("❌ Torrent creation failed")
            messagebox.showerror("Error", f"❌ Failed to create torrent!\n\n{error_msg}")
    
    def open_output_folder(self):
        """Open the output folder in file manager"""
        import subprocess
        import sys
        
        output_dir = self.output_var.get()
        if not output_dir or not Path(output_dir).exists():
            return
        
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", output_dir])
            elif sys.platform == "darwin":
                subprocess.run(["open", output_dir])
            else:
                subprocess.run(["xdg-open", output_dir])
        except Exception:
            pass  # Fail silently if can't open folder
