"""
Configuration GUI Window
Allows users to configure qBittorrent settings
"""
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

from ..core.config_manager import ConfigManager, ConfigError


class ConfigWindow:
    """Configuration window for qBittorrent settings"""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[tk.Tk] = None):
        if not HAS_TKINTER:
            raise RuntimeError("tkinter is required for GUI mode")
        
        self.config_manager = config_manager
        self.parent = parent
        self.window = None
        self.config = None
        
        # Form variables
        self.vars = {}
    
    def show(self):
        """Show the configuration window"""
        if self.window:
            self.window.lift()
            return
        
        # Create window
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("qBittorrent Configuration")
        self.window.geometry("600x700")
        self.window.resizable(True, True)
        
        # Load current configuration
        self.config = self.config_manager.get_config()  # This ensures config is loaded
        
        self.setup_ui()
        
        # Make window modal if it has a parent
        if self.parent:
            self.window.transient(self.parent)
            self.window.grab_set()
    
    def setup_ui(self):
        """Setup the configuration UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # qBittorrent connection tab
        qbit_frame = ttk.Frame(notebook)
        notebook.add(qbit_frame, text="qBittorrent Connection")
        self.create_qbittorrent_tab(qbit_frame)
        
        # Torrent settings tab
        torrent_frame = ttk.Frame(notebook)
        notebook.add(torrent_frame, text="Torrent Settings")
        self.create_torrent_tab(torrent_frame)
        
        # Application settings tab
        app_frame = ttk.Frame(notebook)
        notebook.add(app_frame, text="Application")
        self.create_app_tab(app_frame)
        
        # Button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Buttons
        ttk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_connection
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self.save_config
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_qbittorrent_tab(self, parent):
        """Create qBittorrent connection settings tab"""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Connection settings
        conn_frame = ttk.LabelFrame(scrollable_frame, text="Connection", padding="10")
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Host
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['host'] = tk.StringVar(value=self.config.qbittorrent.host)
        ttk.Entry(conn_frame, textvariable=self.vars['host'], width=30).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Port
        ttk.Label(conn_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['port'] = tk.StringVar(value=str(self.config.qbittorrent.port))
        ttk.Entry(conn_frame, textvariable=self.vars['port'], width=10).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Username
        ttk.Label(conn_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['username'] = tk.StringVar(value=self.config.qbittorrent.username)
        ttk.Entry(conn_frame, textvariable=self.vars['username'], width=30).grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Password
        ttk.Label(conn_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['password'] = tk.StringVar(value=self.config.qbittorrent.password)
        ttk.Entry(conn_frame, textvariable=self.vars['password'], show="*", width=30).grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        # Paths
        paths_frame = ttk.LabelFrame(scrollable_frame, text="Paths", padding="10")
        paths_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Category
        ttk.Label(paths_frame, text="Category:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['category'] = tk.StringVar(value=self.config.qbittorrent.category)
        ttk.Entry(paths_frame, textvariable=self.vars['category'], width=30).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Save path
        ttk.Label(paths_frame, text="Save Path:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['save_path'] = tk.StringVar(value=self.config.qbittorrent.save_path)
        ttk.Entry(paths_frame, textvariable=self.vars['save_path'], width=50).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Options
        options_frame = ttk.LabelFrame(scrollable_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X)
        
        # Auto add after creation
        self.vars['auto_add'] = tk.BooleanVar(value=self.config.qbittorrent.auto_add_after_creation)
        ttk.Checkbutton(
            options_frame,
            text="Automatically add torrents to qBittorrent after creation",
            variable=self.vars['auto_add']
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Auto torrent management
        self.vars['auto_management'] = tk.BooleanVar(value=self.config.qbittorrent.auto_torrent_management)
        ttk.Checkbutton(
            options_frame,
            text="Enable automatic torrent management",
            variable=self.vars['auto_management']
        ).grid(row=1, column=0, sticky=tk.W)
        
        # Trackers
        trackers_frame = ttk.LabelFrame(scrollable_frame, text="Trackers", padding="10")
        trackers_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(trackers_frame, text="Trackers (one per line):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Label(trackers_frame, text="💡 Use ${TRACKER} for environment variables", font=("TkDefaultFont", 8)).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Create text widget for multiple trackers
        tracker_text = tk.Text(trackers_frame, height=4, width=60)
        tracker_text.grid(row=2, column=0, sticky=tk.W+tk.E, pady=(0, 5))
        
        # Populate with current trackers
        current_trackers = self.config.qbittorrent.trackers or []
        tracker_text.insert('1.0', '\n'.join(current_trackers))
        self.vars['trackers_text'] = tracker_text
        
        # Add scrollbar for tracker text
        tracker_scroll = ttk.Scrollbar(trackers_frame, orient="vertical", command=tracker_text.yview)
        tracker_scroll.grid(row=2, column=1, sticky=tk.N+tk.S)
        tracker_text.configure(yscrollcommand=tracker_scroll.set)
    
    def create_torrent_tab(self, parent):
        """Create torrent creation settings tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format settings
        format_frame = ttk.LabelFrame(main_frame, text="Torrent Format", padding="10")
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Format selection
        ttk.Label(format_frame, text="Format:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['format'] = tk.StringVar(value=self.config.torrent_creation.format)
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.vars['format'],
            values=["v1", "v2", "hybrid"],
            state="readonly",
            width=15
        )
        format_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Private
        self.vars['private'] = tk.BooleanVar(value=self.config.torrent_creation.private)
        ttk.Checkbutton(
            options_frame,
            text="Create private torrents by default",
            variable=self.vars['private']
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Start seeding
        self.vars['start_seeding'] = tk.BooleanVar(value=self.config.torrent_creation.start_seeding)
        ttk.Checkbutton(
            options_frame,
            text="Start seeding immediately after creation",
            variable=self.vars['start_seeding']
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Comment
        ttk.Label(options_frame, text="Comment:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['comment'] = tk.StringVar(value=self.config.torrent_creation.comment)
        ttk.Entry(options_frame, textvariable=self.vars['comment'], width=50).grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Timeouts
        timeout_frame = ttk.LabelFrame(main_frame, text="Timeouts", padding="10")
        timeout_frame.pack(fill=tk.X)
        
        # Creation timeout
        ttk.Label(timeout_frame, text="Creation timeout (seconds):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['timeout'] = tk.StringVar(value=str(self.config.torrent_creation.timeout))
        ttk.Entry(timeout_frame, textvariable=self.vars['timeout'], width=10).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
    
    def create_app_tab(self, parent):
        """Create application settings tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Default paths
        paths_frame = ttk.LabelFrame(main_frame, text="Default Paths", padding="10")
        paths_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Default output directory
        ttk.Label(paths_frame, text="Default output directory:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.vars['default_output'] = tk.StringVar(value=self.config.default_output_dir)
        ttk.Entry(paths_frame, textvariable=self.vars['default_output'], width=50).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Behavior
        behavior_frame = ttk.LabelFrame(main_frame, text="Behavior", padding="10")
        behavior_frame.pack(fill=tk.X)
        
        # Remember last folder
        self.vars['remember_folder'] = tk.BooleanVar(value=self.config.remember_last_folder)
        ttk.Checkbutton(
            behavior_frame,
            text="Remember last selected folder",
            variable=self.vars['remember_folder']
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Auto open output folder
        self.vars['auto_open_output'] = tk.BooleanVar(value=self.config.auto_open_output_folder)
        ttk.Checkbutton(
            behavior_frame,
            text="Automatically open output folder after creation",
            variable=self.vars['auto_open_output']
        ).grid(row=1, column=0, sticky=tk.W)
    
    def test_connection(self):
        """Test qBittorrent connection with current settings"""
        try:
            # Create temporary config with current values
            temp_config = self.config_manager.get_config()
            
            # Update with current form values
            temp_config.qbittorrent.host = self.vars['host'].get()
            temp_config.qbittorrent.port = int(self.vars['port'].get())
            temp_config.qbittorrent.username = self.vars['username'].get()
            temp_config.qbittorrent.password = self.vars['password'].get()
            
            # Test connection (this would need to be async in a real implementation)
            # For now, just validate the config
            valid, message = self.config_manager.validate_qbittorrent_config()
            
            if valid:
                messagebox.showinfo("Connection Test", "✅ Configuration appears valid!\n\nNote: Actual connection test requires running qBittorrent.")
            else:
                messagebox.showerror("Connection Test", f"❌ Configuration error:\n\n{message}")
                
        except ValueError as e:
            messagebox.showerror("Connection Test", f"❌ Invalid port number: {self.vars['port'].get()}")
        except Exception as e:
            messagebox.showerror("Connection Test", f"❌ Error: {e}")
    
    def save_config(self):
        """Save configuration"""
        try:
            # Validate and update configuration
            self.config.qbittorrent.host = self.vars['host'].get().strip()
            self.config.qbittorrent.port = int(self.vars['port'].get())
            self.config.qbittorrent.username = self.vars['username'].get().strip()
            self.config.qbittorrent.password = self.vars['password'].get()
            self.config.qbittorrent.category = self.vars['category'].get().strip()
            self.config.qbittorrent.save_path = self.vars['save_path'].get().strip()
            self.config.qbittorrent.auto_add_after_creation = self.vars['auto_add'].get()
            self.config.qbittorrent.auto_torrent_management = self.vars['auto_management'].get()
            
            # Handle trackers
            tracker_text = self.vars['trackers_text'].get('1.0', tk.END).strip()
            trackers = [line.strip() for line in tracker_text.split('\n') if line.strip()]
            self.config.qbittorrent.trackers = trackers
            
            self.config.torrent_creation.format = self.vars['format'].get()
            self.config.torrent_creation.private = self.vars['private'].get()
            self.config.torrent_creation.start_seeding = self.vars['start_seeding'].get()
            self.config.torrent_creation.comment = self.vars['comment'].get()
            self.config.torrent_creation.timeout = int(self.vars['timeout'].get())
            
            self.config.default_output_dir = self.vars['default_output'].get().strip()
            self.config.remember_last_folder = self.vars['remember_folder'].get()
            self.config.auto_open_output_folder = self.vars['auto_open_output'].get()
            
            # Validate configuration
            valid, message = self.config_manager.validate_qbittorrent_config()
            if not valid:
                messagebox.showerror("Configuration Error", f"❌ {message}")
                return
            
            # Save configuration
            self.config_manager.save_config()
            messagebox.showinfo("Success", "✅ Configuration saved successfully!")
            
            self.close()
            
        except ValueError as e:
            messagebox.showerror("Configuration Error", f"❌ Invalid value: {e}")
        except ConfigError as e:
            messagebox.showerror("Configuration Error", f"❌ {e}")
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to save configuration: {e}")
    
    def cancel(self):
        """Cancel configuration changes"""
        self.close()
    
    def close(self):
        """Close the configuration window"""
        if self.window:
            if self.parent:
                self.window.grab_release()
            self.window.destroy()
            self.window = None
    
    def run(self):
        """Run the configuration window as standalone"""
        if not self.window:
            self.show()
        if self.window:
            self.window.mainloop()
