/**
 * Torrent Creator Alpine.js Component
 * Enhanced with Auto-Animate, Form Persistence, and Toast Notifications
 */

function torrentCreator() {
    return {
        // Form State
        form: {
            path: '',
            mode: 'folder', // 'file' or 'folder'
            totalBytes: null,
            fileCount: null,
            
            pieceSizeMode: 'auto', // 'auto' or 'manual'
            pieceSizeBytes: null,
            manualPieceSize: 262144, // 256 KiB default
            targetPieces: 2500,
            
            privateTorrent: true,
            startSeeding: false,
            ignoreShareRatio: false,
            
            optimizeAlignment: false,
            alignThresholdBytes: null,
            
            trackerUrls: '',
            webSeeds: '',
            comment: '',
            source: ''
        },
        
        // Computed properties
        get pieceCount() {
            return this.getPieceCount();
        },
        
        // UI state object
        ui: {
            isScanning: false,
            isCalculating: false,
            isCreating: false,
            showAdvanced: false,
            progressPhase: '',
            progressPercent: 0
        },
        
        // Validation state
        trackerValidation: [],
        trackerTiers: [],
        efficiency: null,
        
        // Method to validate tracker URLs
        validateTrackers() {
            const lines = this.form.trackerUrls.split('\n');
            this.trackerValidation = [];
            this.trackerTiers = [];
            
            let currentTier = [];
            let lineNumber = 1;
            
            for (const line of lines) {
                const trimmed = line.trim();
                
                if (trimmed === '') {
                    // Empty line - start new tier
                    if (currentTier.length > 0) {
                        this.trackerTiers.push([...currentTier]);
                        currentTier = [];
                    }
                } else {
                    // Validate URL
                    const isValid = this.isValidTrackerUrl(trimmed);
                    this.trackerValidation.push({
                        line: lineNumber,
                        valid: isValid,
                        message: isValid ? 'Valid tracker URL' : 'Invalid URL format'
                    });
                    
                    if (isValid) {
                        currentTier.push(trimmed);
                    }
                }
                
                lineNumber++;
            }
            
            // Add final tier
            if (currentTier.length > 0) {
                this.trackerTiers.push(currentTier);
            }
        },
        
        isValidTrackerUrl(url) {
            try {
                const parsed = new URL(url);
                return ['http:', 'https:', 'udp:'].includes(parsed.protocol);
            } catch {
                return false;
            }
        },
        
        // File Browser State
        browser: {
            isOpen: false,
            loading: false,
            error: null,
            currentPath: '/',
            parentPath: '/',
            entries: []
        },
        
        // Computed Properties
        get formattedSize() {
            if (!this.form.totalBytes) return null;
            return this.formatBytes(this.form.totalBytes);
        },
        
        get canCalculate() {
            return this.form.totalBytes !== null && this.form.totalBytes > 0;
        },
        
        get canCreate() {
            return this.form.path && this.form.path.trim() !== '' && 
                   this.form.totalBytes && this.form.totalBytes > 0 &&
                   (!this.trackerValidation.length || this.trackerValidation.every(v => !v.isError));
        },
        
        get calculatedPieceSize() {
            if (this.form.pieceSizeMode === 'manual') {
                return this.form.manualPieceSize;
            }
            
            if (!this.form.totalBytes) return null;
            
            // Auto-calculate optimal piece size
            const bytes = this.form.totalBytes;
            const targetPieces = this.form.targetPieces;
            
            let pieceSize = Math.ceil(bytes / targetPieces);
            
            // Round to nearest power of 2 that's >= 16 KiB
            const minSize = 16 * 1024;
            pieceSize = Math.max(minSize, 1 << Math.ceil(Math.log2(pieceSize)));
            
            return pieceSize;
        },
        
        get pieceCount() {
            if (!this.form.totalBytes || !this.calculatedPieceSize) return null;
            return Math.ceil(this.form.totalBytes / this.calculatedPieceSize);
        },
        
        // Initialization
        init() {
            console.log('Torrent Creator component initialized');
            
            // Initialize entries as an empty array to prevent errors
            if (!this.browser.entries) {
                this.browser = {
                    isOpen: false,
                    isLoading: false,
                    error: null,
                    currentPath: '/',
                    parentPath: '/',
                    entries: [],
                    history: ['/'],
                    filter: '',
                    showHidden: false
                };
                console.log('Browser object initialized with default values:', this.browser);
            } else {
                console.log('Browser object already exists:', this.browser);
            }
            
            // Initialize tracker validation
            this.validateTrackers();
            
            // Global helper to detect if an entry is a directory using multiple signals
            this.isDirectory = (entry) => {
                // 1. Check explicit is_directory or is_dir flag
                if (entry.is_directory === true || entry.is_dir === true) {
                    console.log('Directory detected by is_directory flag:', entry.name);
                    return true;
                }
                
                // 2. Check for trailing slash in various properties
                if (entry.name && entry.name.endsWith('/')) {
                    console.log('Directory detected by trailing slash in name:', entry.name);
                    return true;
                }
                
                if (entry.display_name && entry.display_name.endsWith('/')) {
                    console.log('Directory detected by trailing slash in display_name:', entry.display_name);
                    return true;
                }
                
                if (entry.path && entry.path.endsWith('/')) {
                    console.log('Directory detected by trailing slash in path:', entry.path);
                    return true;
                }
                
                // 3. Check _isDirectory flag (might have been set during normalization)
                if (entry._isDirectory === true) {
                    console.log('Directory detected by _isDirectory flag:', entry.name);
                    return true;
                }
                
                // 4. Infer from name (common folder names)
                const commonFolderNames = ['data', 'downloads', 'torrents', 'movies', 'tv', 'music', 'documents', 'pictures'];
                if (entry.name && commonFolderNames.includes(entry.name.toLowerCase())) {
                    console.log('Directory inferred from common folder name:', entry.name);
                    return true;
                }
                
                // 5. Special case for qBittorrent API: folders might not have sizes
                if (!entry.size && !entry.file_size && entry.original_name && 
                     entry.original_name.includes('/')) {
                    console.log('Directory detected from original_name pattern and no size:', entry.name);
                    return true;
                }
                
                return false;
            };
            
            // Add a utility method to fix paths and improve directory detection
            this.normalizeApiPaths = (entries, currentPath) => {
                if (!Array.isArray(entries)) return entries;
                
                return entries.map(entry => {
                    let normalized = { ...entry };
                    
                    // Always preserve the original name before any modifications
                    if (normalized.name) {
                        normalized.original_name = normalized.name;
                    }
                    
                    // Extract just the basename if name contains full path
                    if (normalized.name && normalized.name.includes('/')) {
                        // Get the basename (last part of the path)
                        const parts = normalized.name.split('/').filter(Boolean);
                        if (parts.length > 0) {
                            normalized.name = parts[parts.length - 1];
                        }
                    }
                    
                    // Check for names with leading spaces (like '/ data')
                    if (normalized.name && normalized.name.startsWith(' ')) {
                        console.log('Found name with leading space:', normalized.name);
                        // Trim the name but keep the original in original_name
                        normalized.name = normalized.name.trim();
                    }
                    
                    // Fix path duplications in the entry.path
                    if (normalized.path) {
                        // Detect if the current path is already in the entry path
                        if (currentPath && currentPath !== '/' && normalized.path.includes(currentPath + '/')) {
                            // Check if we have a duplication
                            const pathParts = normalized.path.split(currentPath);
                            if (pathParts.length > 2) {
                                // We have a duplication - fix it
                                normalized.path = currentPath + pathParts[pathParts.length - 1];
                                console.log('Fixed duplicated path:', entry.path, '->', normalized.path);
                            }
                        }
                        
                        // Remove any double slashes
                        normalized.path = normalized.path.replace(/\/+/g, '/');
                    }
                    
                    // Improve directory detection with multiple signals
                    normalized._isDirectory = this.isDirectory(normalized);
                    
                    return normalized;
                });
            };
            
            // Check if autoAnimate is loaded and available
            if (typeof window.autoAnimate === 'function') {
                // Apply auto-animate to appropriate containers
                document.querySelectorAll('[x-auto-animate]').forEach(el => {
                    window.autoAnimate(el);
                });
                
                this.$nextTick(() => {
                    if (this.$refs.progressLogs) {
                        window.autoAnimate(this.$refs.progressLogs);
                    }
                });
            } else {
                console.log('autoAnimate is not available - skipping animation');
            }
            
            // Load default qBittorrent paths
            this.loadDefaultPaths();
        },
        
        // Load default qBittorrent paths
        loadDefaultPaths() {
            fetch('/api/qbittorrent/default-paths')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to load default paths: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.defaultSavePath) {
                        // If we don't have a path set already, use the qBittorrent default save path
                        if (!this.form.path || this.form.path.trim() === '') {
                            // Normalize the path to prevent double slashes
                            const normalizedPath = data.defaultSavePath.replace(/\/+/g, '/');
                            this.form.path = normalizedPath;
                            console.log('Using normalized default save path:', normalizedPath);
                        }
                        console.log('Loaded default qBittorrent paths:', data);
                    }
                })
                .catch(error => {
                    console.error('Error loading default paths:', error);
                });
        },

        // Helper to get parent path
        getParentPath(path) {
            if (!path || path === '/' || path === '') {
                return '/';
            }
            
            // Remove trailing slash if present
            const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;
            
            // Get the last index of '/' and return everything before it
            const lastSlashIndex = normalizedPath.lastIndexOf('/');
            if (lastSlashIndex <= 0) {
                return '/'; // If slash is at the beginning or not found, return root
            }
            
            return normalizedPath.substring(0, lastSlashIndex) || '/';
        },
        
        // Path change handler
        pathChanged() {
            // Reset scan results when path changes
            this.form.totalBytes = null;
            this.form.fileCount = null;
            this.form.pieceSizeBytes = null;
            this.efficiency = null;
        },

        // File Browser Methods
        browseFile() {
            this.form.mode = 'file';
            this.openFileBrowser();
        },
        
        browseFolder() {
            this.form.mode = 'folder';
            this.openFileBrowser();
        },
        
        openFileBrowser() {
            console.log('Opening file browser...');
            console.log('Current mode:', this.form.mode);
            
            this.browser.isOpen = true;
            this.browser.isLoading = true;  // Changed from loading to isLoading
            this.browser.error = null;
            this.browser.entries = [];
            
            // Start at the current path or root if none set
            // If we're continuing navigation, use the current browser path
            const startPath = this.form.path && this.form.path.trim() 
                ? this.form.path 
                : (this.browser.currentPath || '/');
                
            console.log('Starting browser at path:', startPath);
            this.navigateToPath(startPath);
        },
        
        navigateToPath(path) {
            console.log('Navigating to path:', path);
            
            // Normalize path to prevent double slashes
            let normalizedPath = path.replace(/\/+/g, '/');
            console.log('Normalized path:', normalizedPath);
            
            this.browser.currentPath = normalizedPath;
            this.browser.isLoading = true;  // Changed from loading to isLoading
            this.browser.error = null;
            
            // Use the qBittorrent API browsing endpoint instead of the local filesystem
            fetch('/api/qbittorrent/browse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ path: normalizedPath })
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Directory data received:', data);
                    
                    // Extract the current path from the response or use the one we set
                    const responsePath = data.current_path || normalizedPath;
                    
                    // Handle the qBittorrent API response format
                    if (data.success === true && Array.isArray(data.entries)) {
                        // qBittorrent API format detected
                        // Fix paths in entries to prevent duplicated segments
                        this.browser.entries = this.normalizeApiPaths(data.entries, responsePath);
                        this.browser.parentPath = data.parent_path || this.getParentPath(this.browser.currentPath);
                        this.browser.isLoading = false;
                    } else if (data.entries && Array.isArray(data.entries)) {
                        // Another variation of qBittorrent response
                        this.browser.entries = this.normalizeApiPaths(data.entries, responsePath);
                        this.browser.parentPath = data.parent_path || this.getParentPath(this.browser.currentPath);
                        this.browser.isLoading = false;
                    } else if (data.files && Array.isArray(data.files)) {
                        // Standard /api/browse format
                        this.browser.entries = this.normalizeApiPaths(data.files, responsePath);
                        this.browser.parentPath = data.parent || this.getParentPath(this.browser.currentPath);
                        this.browser.isLoading = false;
                    } else {
                        // Unknown format, try to extract entries if possible
                        console.log('Trying to extract entries from response:', data);
                        if (Array.isArray(data)) {
                            this.browser.entries = this.normalizeApiPaths(data, responsePath);
                        } else if (data.content && Array.isArray(data.content)) {
                            this.browser.entries = this.normalizeApiPaths(data.content, responsePath);
                        } else {
                            this.browser.entries = [];
                            this.browser.error = 'Unexpected response format from server';
                        }
                        this.browser.parentPath = this.getParentPath(this.browser.currentPath);
                        this.browser.isLoading = false;
                    }
                })
                .catch(error => {
                    console.error('Error browsing directory:', error);
                    this.browser.error = `Failed to load directory: ${error.message}`;
                    this.browser.entries = [];
                    this.browser.isLoading = false;
                });
        },
        
        navigateUp() {
            if (this.browser.parentPath) {
                this.navigateToPath(this.browser.parentPath);
            }
        },
        
        // Helper to get the full path for an entry
        getEntryPath(entry) {
            console.log('Getting entry path from:', entry);
            
            // Check if path contains a duplicate path pattern like "/some/path//some/path/"
            const containsDuplicatePath = (path) => {
                if (!path) return false;
                // Look for double slash followed by a segment that's already in the path
                const parts = path.split('//');
                if (parts.length <= 1) return false;
                
                // Check if right part contains segments from left part
                const leftPart = parts[0];
                const rightPart = parts[1];
                
                return rightPart.includes(leftPart);
            };
            
            // Fix path with duplicate segments
            const fixDuplicatePath = (path) => {
                if (!path) return path;
                
                // First normalize all consecutive slashes to single slash
                let normalized = path.replace(/\/+/g, '/');
                
                // Handle case where the entry name is already a full path
                // Example: "/data/downloads/torrents//data/downloads/torrents/qbittorrent"
                // Should become just "/data/downloads/torrents/qbittorrent"
                const parts = path.split('//');
                if (parts.length > 1) {
                    // Check if the part after '//' is duplicated
                    const leftPart = parts[0];
                    const rightPart = parts[1];
                    
                    // If right part starts with segments from left part, get the unique part
                    if (rightPart.includes('/')) {
                        // Extract the common base path and unique part
                        const rightSegments = rightPart.split('/');
                        const leftSegments = leftPart.split('/').filter(Boolean);
                        
                        // Find how many segments match from the beginning
                        let matchedSegments = 0;
                        for (let i = 0; i < Math.min(leftSegments.length, rightSegments.length); i++) {
                            if (rightSegments[i] === leftSegments[i]) {
                                matchedSegments++;
                            } else {
                                break;
                            }
                        }
                        
                        // Get the unique part from the right segments
                        if (matchedSegments > 0) {
                            const uniquePart = rightSegments.slice(matchedSegments).join('/');
                            normalized = leftPart + '/' + uniquePart;
                            console.log('Fixed duplicate path segments. Original:', path, 'Fixed:', normalized);
                        }
                    } else {
                        // Simple case: just use the left part
                        normalized = leftPart;
                    }
                }
                
                return normalized;
            };
            
            // Handle various API formats with path normalization
            if (entry.path) {
                console.log('Using entry.path:', entry.path);
                
                if (containsDuplicatePath(entry.path)) {
                    const fixedPath = fixDuplicatePath(entry.path);
                    console.log('Fixed duplicate path:', fixedPath);
                    return fixedPath;
                }
                
                // If the entry.path already contains the full path, don't append to current path
                if (entry.path.startsWith('/')) {
                    return entry.path.replace(/\/+/g, '/'); // Normalize slashes
                }
                
                // Normalize path if it's relative to current path
                const currentPath = this.browser.currentPath;
                const basePath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
                return (basePath + entry.path).replace(/\/+/g, '/');
            }
            
            if (entry.file_path) {
                console.log('Using entry.file_path:', entry.file_path);
                
                if (containsDuplicatePath(entry.file_path)) {
                    const fixedPath = fixDuplicatePath(entry.file_path);
                    console.log('Fixed duplicate file_path:', fixedPath);
                    return fixedPath;
                }
                
                // Same normalization for file_path
                if (entry.file_path.startsWith('/')) {
                    return entry.file_path.replace(/\/+/g, '/'); // Normalize slashes
                }
                
                const currentPath = this.browser.currentPath;
                const basePath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
                return (basePath + entry.file_path).replace(/\/+/g, '/');
            }
            
            // If the entry has a name that's already a full path (starting with '/')
            if (entry.name && entry.name.startsWith('/')) {
                // Extract just the basename component for the current directory
                const currentPath = this.browser.currentPath;
                const baseName = entry.name.split('/').filter(Boolean).pop() || '';
                
                console.log('Using basename from entry.name:', baseName);
                const basePath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
                return (basePath + baseName).replace(/\/+/g, '/');
            }
            
            // If no direct path, construct from current path and entry name
            const currentPath = this.browser.currentPath;
            const entryName = entry.name || entry.filename || '';
            const basePath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
            const constructedPath = (basePath + entryName).replace(/\/+/g, '/');
            
            console.log('Constructed path from currentPath and name:', constructedPath);
            return constructedPath;
        },
        
        selectEntry(entry) {
            console.log('Entry selected:', entry);
            
            console.log('Is directory:', this.isDirectory(entry));
            const entryPath = this.getEntryPath(entry);
            console.log('Using path:', entryPath);
            
            if (this.isDirectory(entry)) {
                // It's a directory - navigate into it
                console.log('Navigating to directory:', entryPath);
                this.navigateToPath(entryPath);
            } else if (this.form.mode === 'file') {
                // It's a file and we're in file selection mode - select it
                console.log('Selecting file path:', entryPath);
                this.selectPath(entryPath);
            } else {
                // It's a file but we're in folder selection mode - notify user
                console.log('Cannot select file in folder mode');
                if (window.$store && window.$store.notifications) {
                    window.$store.notifications.warning('Please select a folder, not a file');
                }
            }
        },
        
        selectCurrentDirectory() {
            console.log('Selecting current directory:', this.browser.currentPath);
            
            if (this.form.mode === 'folder') {
                // Set form path but don't close browser - for "Select This Folder" button
                let normalizedPath = this.browser.currentPath.replace(/\/+/g, '/');
                console.log('Current directory normalized path:', normalizedPath);
                
                this.form.path = normalizedPath;
                // Close the browser and proceed with the selection
                this.browser.isOpen = false;
                this.pathChanged();
                
                // Auto-scan the selected path
                this.scanPath();
            }
        },
        
        selectPath(path) {
            console.log('Path selected:', path);
            
            // Normalize path to prevent double slashes
            let normalizedPath = path.replace(/\/+/g, '/');
            console.log('Normalized selected path:', normalizedPath);
            
            // Update the form with the new path
            this.form.path = normalizedPath;
            
            // Check if this is a file selection (from selectEntry) or folder selection (from selectCurrentDirectory)
            // Only close the browser if it's explicitly a file selection in file mode or a folder selection in folder mode
            if ((this.form.mode === 'file' && !normalizedPath.endsWith('/')) || 
                (this.form.mode === 'folder' && this.browser.currentPath === normalizedPath)) {
                console.log('Final selection made, closing browser');
                this.browser.isOpen = false;
                this.pathChanged();
                
                // Reset any previous scan errors
                this.ui.isScanError = false;
                this.ui.scanErrorMessage = null;
                
                // Reset previous scan results before new scan
                this.resetScanResults();
                
                // Auto-scan the selected path
                console.log('Triggering scan path after final selection');
                this.scanPath();
                
                // Log scan results after a short delay
                setTimeout(() => {
                    console.log('Path selection scan results:', {
                        totalBytes: this.form.totalBytes,
                        fileCount: this.form.fileCount,
                        mode: this.form.mode
                    });
                }, 1000);
            } else {
                // This is likely just navigation, don't close the browser
                console.log('Keeping browser open for further navigation');
            }
        },
        
        cancelBrowse() {
            this.browser.isOpen = false;
        },
        
        // Calculate pieces - use the advanced API
        async calculatePieces() {
            if (!this.canCalculate) return;
            
            this.ui.isCalculating = true;
            
            try {
                // Use the more advanced qBittorrent analysis API for detailed information
                const response = await fetch('/api/qbittorrent/calculate-pieces', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        path: this.form.path,
                        targetPieces: this.form.targetPieces
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Calculation failed: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Update form with the calculated data
                this.form.pieceSizeBytes = data.pieceSize;
                this.efficiency = data.efficiency;
                
                // Show notification if available
                if (window.$store && window.$store.notifications) {
                    window.$store.notifications.success(`Calculated pieces: ${this.formatBytes(data.pieceSize)} × ${data.pieceCount}`);
                }
                
            } catch (error) {
                console.error('Piece calculation error:', error);
                
                // Fallback to client-side calculation
                this.form.pieceSizeBytes = this.calculatedPieceSize;
                
                // Show error notification if available
                if (window.$store && window.$store.notifications) {
                    window.$store.notifications.error('Calculation error: ' + error.message);
                }
                
            } finally {
                this.ui.isCalculating = false;
            }
        },
        
        // Progress tracking
        progress: {
            stage: 'idle',
            percentage: 0,
            message: 'Ready',
            logs: []
        },
        
        // Handle piece size mode change
        pieceSizeModeChanged() {
            if (this.form.pieceSizeMode === 'auto' && this.form.totalBytes) {
                // Recalculate with the qBittorrent API
                this.calculatePieces();
            } else if (this.form.pieceSizeMode === 'manual') {
                // Use the manual selection
                this.form.pieceSizeBytes = this.form.manualPieceSize;
            }
        },
        
        // Path Scanning
        async scanPath() {
            if (!this.form.path.trim()) {
                this.resetScanResults();
                return;
            }
            
            this.ui.isScanning = true;

            try {
                // Normalize the path to prevent issues with duplicate segments
                const normalizedPath = this.form.path.replace(/\/+/g, '/');
                console.log('Scanning normalized path:', normalizedPath);
                
                // Use the qBittorrent API scan endpoint instead of the local filesystem
                const response = await fetch('/api/qbittorrent/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: normalizedPath })
                });

                if (!response.ok) {
                    throw new Error(`Scan failed: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Scan response data:', data);
                
                this.form.totalBytes = data.totalBytes || 0;
                this.form.fileCount = data.fileCount || 0;
                this.form.mode = data.mode || this.form.mode;
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Update UI with complete scan information
                this.ui.scanComplete = true;
                
                // Show toast notification if available
                if (window.$store && window.$store.notifications) {
                    window.$store.notifications.success(`Scanned: ${this.formatBytes(data.totalBytes)}, ${data.fileCount} files`);
                }
                
                // Calculate optimal piece size using qBittorrent API
                if (this.form.pieceSizeMode === 'auto') {
                    await this.calculatePieces();
                }
                
                console.log('Updated form data after scan:', {
                    totalBytes: this.form.totalBytes,
                    fileCount: this.form.fileCount,
                    mode: this.form.mode,
                    pieceSize: this.form.pieceSize
                });
                
            } catch (error) {
                console.error('Scan error:', error);
                this.ui.isScanError = true;
                this.ui.scanErrorMessage = error.message || 'Unknown error occurred during scan';
                
                // Show toast notification if available
                if (window.$store && window.$store.notifications) {
                    window.$store.notifications.error(`Scan failed: ${error.message}`);
                }
                
                this.resetScanResults();
                console.log('Scan results reset due to error');
            } finally {
                this.ui.isScanning = false;
            }
        },

        resetScanResults() {
            this.form.totalBytes = null;
            this.form.fileCount = null;
            this.ui.scanComplete = false;
            console.log('Scan results reset');
        },
        
        // Calculate the number of pieces based on total size and piece size
        getPieceCount() {
            if (!this.form.totalBytes) {
                return 0;
            }
            
            // Use pieceSize if available, otherwise use a default value
            const pieceSize = this.form.pieceSize || 256; // Default to 256 KB if not set
            
            // Convert piece size from KB to bytes
            const pieceSizeBytes = pieceSize * 1024;
            
            // Calculate and return the number of pieces
            return Math.ceil(this.form.totalBytes / pieceSizeBytes);
        },
        
        // Torrent Creation
        async createTorrent() {
            if (!this.validateForm()) return;

            this.creating = true;
            this.showProgress = true;
            this.progress = {
                stage: 'starting',
                percentage: 0,
                message: 'Starting torrent creation...',
                logs: []
            };

            try {
                const formData = this.buildFormData();
                
                // Use Server-Sent Events for progress tracking
                const eventSource = new EventSource('/api/create/stream?' + new URLSearchParams(formData));
                
                eventSource.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.updateProgress(data);
                };
                
                eventSource.onerror = (error) => {
                    console.error('SSE Error:', error);
                    eventSource.close();
                    this.handleCreationError('Connection error during torrent creation');
                };
                
                eventSource.addEventListener('complete', (event) => {
                    const data = JSON.parse(event.data);
                    eventSource.close();
                    this.handleCreationComplete(data);
                });
                
                eventSource.addEventListener('error', (event) => {
                    const data = JSON.parse(event.data);
                    eventSource.close();
                    this.handleCreationError(data.message || 'Unknown error');
                });
                
            } catch (error) {
                console.error('Creation error:', error);
                this.handleCreationError(error.message);
            }
        },

        async createTorrentBasic() {
            if (!this.validateForm()) return;

            this.creating = true;
            this.showProgress = true;
            this.progress = {
                stage: 'creating',
                percentage: 0,
                message: 'Creating torrent...',
                logs: []
            };

            try {
                const formData = this.buildFormData();
                
                const response = await fetch('/api/create-enhanced', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) {
                    throw new Error(`Creation failed: ${response.statusText}`);
                }

                const result = await response.json();
                this.handleCreationComplete(result);
                
            } catch (error) {
                console.error('Creation error:', error);
                this.handleCreationError(error.message);
            }
        },

        validateForm() {
            // Check if path is provided
            if (!this.form.path.trim()) {
                this.showToast('Please select a file or folder path', 'error');
                return false;
            }
            
            // Check if scan completed successfully
            if (!this.form.totalBytes) {
                this.showToast('Please scan the selected path first', 'error');
                return false;
            }
            
            // Validate trackers if provided
            if (this.form.trackerUrls && this.form.trackerUrls.trim()) {
                // Parse and validate trackers
                this.validateTrackers();
                
                // Check if any trackers are invalid
                const hasInvalidTracker = this.trackerValidation.some(tracker => !tracker.valid);
                
                if (hasInvalidTracker) {
                    this.showToast('One or more tracker URLs are invalid', 'error');
                    return false;
                }
            }
            
            return true;
        },

        buildFormData() {
            return {
                mode: this.form.mode,
                path: this.form.path,
                pieceSizeMode: this.form.pieceSizeMode,
                pieceSizeBytes: this.form.pieceSizeBytes || this.calculatedPieceSize,
                targetPieces: this.form.targetPieces,
                privateTorrent: this.form.privateTorrent,
                startSeeding: this.form.startSeeding,
                ignoreShareRatio: this.form.ignoreShareRatio,
                optimizeAlignment: this.form.optimizeAlignment,
                alignThresholdBytes: this.form.alignThresholdBytes,
                announceTiers: this.form.trackerUrls.split('\n').filter(url => url.trim()).map(url => [url.trim()]),
                webSeeds: this.form.webSeeds.split('\n').filter(url => url.trim()),
                comment: this.form.comment,
                source: this.form.source,
                v2Mode: 'v1',
                // Add navigation mode to use qBittorrent API
                navigationMode: 'qbittorrent'
            };
        },

        updateProgress(data) {
            this.progress = {
                ...this.progress,
                ...data,
                logs: [...this.progress.logs, data.message]
            };
        },

        handleCreationComplete(data) {
            this.creating = false;
            this.progress.stage = 'complete';
            this.progress.percentage = 100;
            this.progress.message = 'Torrent created successfully!';
            
            this.showToast('Torrent created successfully!', 'success');
            
            if (data.torrent_path) {
                // Offer download link
                const link = document.createElement('a');
                link.href = `/api/download/${encodeURIComponent(data.torrent_path)}`;
                link.download = data.filename || 'torrent.torrent';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        },

        handleCreationError(message) {
            this.creating = false;
            this.progress.stage = 'error';
            this.progress.message = message;
            this.showToast('Creation failed: ' + message, 'error');
        },
        
        // Utility Methods
        formatBytes(bytes) {
            if (!bytes) return '0 B';
            
            const sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            
            return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
        },

        formatPieceSize(bytes) {
            if (!bytes) return '';
            
            if (bytes >= 1024 * 1024) {
                return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
            } else {
                return `${(bytes / 1024).toFixed(0)} KiB`;
            }
        },

        showToast(message, type = 'info') {
            // Dispatch custom event for toast system
            window.dispatchEvent(new CustomEvent('show-toast', {
                detail: { message, type }
            }));
        },

        // Reset form
        resetForm() {
            Object.assign(this.form, {
                path: '',
                mode: 'folder',
                totalBytes: null,
                fileCount: null,
                pieceSizeMode: 'auto',
                pieceSizeBytes: null,
                manualPieceSize: 262144,
                targetPieces: 2500,
                privateTorrent: true,
                startSeeding: false,
                ignoreShareRatio: false,
                optimizeAlignment: false,
                alignThresholdBytes: null,
                trackerUrls: '',
                webSeeds: '',
                comment: '',
                source: ''
            });
            
            this.resetScanResults();
            this.showProgress = false;
            this.creating = false;
        }
    };
}

// Make function globally available
window.torrentCreator = torrentCreator;
