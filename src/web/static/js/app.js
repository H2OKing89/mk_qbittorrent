/**
 * Torrent Creator Application
 * Main Alpine.js component for the torrent creation interface
 */

function torrentCreator() {
    return {
        // State
        currentPath: '/',
        folderItems: [],
        selectedFolder: '',
        folderInfo: null,
        outputDir: './torrents',
        uploadRoot: '/mnt/user/data/downloads/torrents/qbittorrent/seedvault/',
        private: true,
        startSeeding: false,
        isLoading: false,
        isCreating: false,
        progress: 0,
        statusMessage: '',
        result: null,
        connectionStatus: null,
        connectionSuccess: false,
        connectionMessage: '',
        dockerMapping: null,  // Docker path mapping info
        showDockerInfo: false,  // Show/hide docker mapping details
        
        // Initialize the application
        async init() {
            await this.loadConfig();
            await this.loadDockerMapping();
            await this.navigateToFolder('/');
        },
        
        // Load configuration from server
        async loadConfig() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                this.outputDir = config.default_output_dir || './torrents';
                this.uploadRoot = config.default_upload_root || '/mnt/user/data/downloads/torrents/qbittorrent/seedvault/';
                this.private = config.torrent_creation?.private ?? true;
                this.startSeeding = config.torrent_creation?.start_seeding ?? false;
            } catch (error) {
                console.error('Failed to load config:', error);
                this.showToast('Failed to load configuration', 'error');
            }
        },
        
        // Load docker mapping information
        async loadDockerMapping() {
            try {
                const response = await fetch('/api/docker-mapping');
                this.dockerMapping = await response.json();
            } catch (error) {
                console.error('Failed to load docker mapping:', error);
                this.dockerMapping = { enabled: false, mappings: {} };
            }
        },
        
        // Navigate to a specific folder
        async navigateToFolder(path) {
            this.isLoading = true;
            try {
                const response = await fetch(`/api/folders?path=${encodeURIComponent(path)}`);
                const data = await response.json();
                this.currentPath = data.current_path;
                this.folderItems = data.items;
                this.selectedFolder = '';
                this.folderInfo = null;
            } catch (error) {
                console.error('Navigation failed:', error);
                this.showToast('Failed to navigate to folder', 'error');
            }
            this.isLoading = false;
        },
        
        // Handle clicks on folder/file items
        handleItemClick(item) {
            if (item.type === 'directory' || item.type === 'parent') {
                this.navigateToFolder(item.path);
            } else {
                // For files, show info but keep current directory context
                console.log('File clicked:', item.name, item.path);
                this.showFileClickMessage(item.name);
            }
        },
        
        // Show message when file is clicked
        showFileClickMessage(fileName) {
            console.log(`File "${fileName}" clicked. Use "✅ Use This Folder" to create torrent from current directory.`);
            this.showToast(`File "${fileName}" selected. Use current directory for torrent creation.`, 'info');
        },
        
        // Select current folder for torrent creation
        selectCurrentFolder() {
            console.log('Selecting folder - currentPath:', this.currentPath);
            console.log('currentPath type check - exists:', !!this.currentPath);
            
            const folderPath = this.currentPath;
            console.log('Using folder path:', folderPath);
            
            this.selectedFolder = folderPath;
            this.getFolderInfo(folderPath);
        },
        
        // Get detailed folder information
        async getFolderInfo(path) {
            try {
                console.log('Getting folder info for:', path);
                const response = await fetch(`/api/folder-info?path=${encodeURIComponent(path)}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('Folder info received:', data);
                this.folderInfo = data;
                
                if (data.is_valid) {
                    this.showToast('Folder ready for torrent creation!', 'success');
                } else {
                    this.showToast(data.validation_message || 'Folder validation failed', 'warning');
                }
                
            } catch (error) {
                console.error('Failed to get folder info:', error);
                this.folderInfo = null;
                this.showToast(`Failed to get folder information: ${error.message}`, 'error');
            }
        },
        
        // Test qBittorrent connection
        async testConnection() {
            this.isLoading = true;
            this.connectionStatus = null;
            
            try {
                const response = await fetch('/api/test-connection', { method: 'POST' });
                const data = await response.json();
                this.connectionSuccess = data.success;
                this.connectionMessage = data.message;
                this.connectionStatus = true;
                
                this.showToast(data.message, data.success ? 'success' : 'error');
                
            } catch (error) {
                this.connectionSuccess = false;
                this.connectionMessage = `Connection failed: ${error.message}`;
                this.connectionStatus = true;
                this.showToast(`Connection failed: ${error.message}`, 'error');
            }
            
            this.isLoading = false;
            
            // Hide status after 5 seconds
            setTimeout(() => {
                this.connectionStatus = null;
            }, 5000);
        },
        
        // Create torrent
        async createTorrent() {
            if (!this.canCreateTorrent()) return;
            
            this.isCreating = true;
            this.progress = 0;
            this.statusMessage = 'Preparing torrent creation...';
            this.result = null;
            
            // Simulate progress with more realistic updates
            const progressInterval = setInterval(() => {
                if (this.progress < 90) {
                    this.progress += Math.random() * 10;
                    if (this.progress < 30) {
                        this.statusMessage = 'Analyzing files...';
                    } else if (this.progress < 60) {
                        this.statusMessage = 'Creating torrent...';
                    } else {
                        this.statusMessage = 'Adding to qBittorrent...';
                    }
                }
            }, 500);
            
            try {
                const response = await fetch('/api/create-torrent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        source_path: this.selectedFolder,
                        output_dir: this.outputDir,
                        private: this.private,
                        start_seeding: this.startSeeding
                    })
                });
                
                this.result = await response.json();
                this.progress = 100;
                this.statusMessage = this.result.success ? 'Completed!' : 'Failed!';
                
                if (this.result.success) {
                    this.showToast('Torrent created successfully!', 'success');
                } else {
                    this.showToast(this.result.error || 'Torrent creation failed', 'error');
                }
                
            } catch (error) {
                this.result = {
                    success: false,
                    error: `Request failed: ${error.message}`
                };
                this.statusMessage = 'Failed!';
                this.showToast(`Request failed: ${error.message}`, 'error');
            }
            
            clearInterval(progressInterval);
            this.isCreating = false;
        },
        
        // Validation for torrent creation
        canCreateTorrent() {
            const result = this.selectedFolder && 
                   this.outputDir && 
                   this.folderInfo?.is_valid && 
                   !this.isCreating;
            
            // Debug logging (can be removed in production)
            if (!result) {
                console.log('Create torrent disabled. Conditions:', {
                    selectedFolder: !!this.selectedFolder,
                    outputDir: !!this.outputDir,
                    folderInfo: !!this.folderInfo,
                    folderInfoValid: this.folderInfo?.is_valid,
                    isCreating: this.isCreating
                });
            }
            
            return result;
        },
        
        // Utility: Format file size in human readable format
        formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        },
        
        // Show toast notifications
        showToast(message, type = 'info') {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            
            // Add to document
            document.body.appendChild(toast);
            
            // Show toast
            setTimeout(() => toast.classList.add('show'), 100);
            
            // Remove toast after 4 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => document.body.removeChild(toast), 300);
            }, 4000);
        },
        
        // Toggle docker mapping info display
        toggleDockerInfo() {
            this.showDockerInfo = !this.showDockerInfo;
        },
        
        // Reset form to initial state
        resetForm() {
            this.selectedFolder = '';
            this.folderInfo = null;
            this.result = null;
            this.progress = 0;
            this.statusMessage = '';
            this.isCreating = false;
            this.connectionStatus = null;
            this.navigateToFolder('/');
        }
    }
}
