/**
 * TorrentCreator Component
 * Main Alpine.js component for torrent creation functionality
 * Matches qBittorrent desktop interface exactly
 */

import { apiClient } from '../core/api-client.js';
import { 
  formatFileSize, 
  formatPieceSize, 
  formatNumber, 
  formatPercentage, 
  debounce, 
  parseTrackerTiers,
  isValidPath
} from '../core/utils.js';

/**
 * TorrentCreator Alpine.js Component
 * Handles all torrent creation functionality with desktop parity
 */
export function TorrentCreator() {
  return {
    // ============================================
    // Component State
    // ============================================
    
    // Form data matching qBittorrent desktop
    form: {
      path: '',
      pieceSizeMode: 'auto',
      pieceSizeBytes: 262144, // 256 KiB default
      targetPieces: 2500,
      privateTorrent: true, // ON by default per spec
      startSeeding: false,
      ignoreShareRatio: false,
      optimizeAlignment: false,
      alignmentThreshold: 0,
      trackerUrls: '',
      webSeeds: '',
      comment: '',
      source: ''
    },
    
    // UI state
    ui: {
      sourceType: 'folder',
      showFileBrowser: false,
      showAdvanced: false,
      isScanning: false,
      isCalculating: false
    },
    
    // Path analysis data - matches desktop display
    pathData: {
      isValid: false,
      isScanning: false,
      totalSize: 0,
      fileCount: 0,
      directoryCount: 0,
      error: null
    },
    
    // Piece calculation data - matches desktop display
    pieceData: {
      pieceCount: 0,
      recommendedSize: 0,
      efficiency: 0,
      options: []
    },
    
    // Tracker validation
    trackerData: {
      isValid: false,
      isValidating: false,
      errors: [],
      tiers: []
    },
    
    // Creation progress - mimics desktop progress bar
    progress: {
      isCreating: false,
      phase: '',
      percentage: 0,
      result: null,
      error: null
    },
    
    // File browser state
    browserPath: '/',
    browserItems: [],
    selectedPath: '',

    // ============================================
    // Computed Properties
    // ============================================
    
    get canCreate() {
      return this.pathData.isValid && 
             this.trackerData.isValid && 
             this.form.path && 
             this.form.trackerUrls &&
             !this.progress.isCreating;
    },
    
    get formattedPathSize() {
      return this.pathData.totalSize > 0 ? formatFileSize(this.pathData.totalSize) : '';
    },
    
    get formattedPieceSize() {
      return this.pieceData.recommendedSize > 0 ? formatPieceSize(this.pieceData.recommendedSize) : '';
    },
    
    get efficiencyColor() {
      if (this.pieceData.efficiency >= 95) return 'text-qbit-success';
      if (this.pieceData.efficiency >= 85) return 'text-qbit-warning';
      return 'text-qbit-error';
    },
    
    get validationSummary() {
      return ValidationService.getValidationSummary(this.form);
    },

    // ============================================
    // Lifecycle Methods
    // ============================================
    
    async init() {
      console.log('🚀 TorrentCreator component initialized');
      
      // Load user preferences
      const preferences = StorageService.loadUserPreferences();
      this.ui.autoSaveEnabled = preferences.autoSaveForm;
      this.ui.showAdvanced = preferences.showAdvancedOptions;
      
      // Load persisted form data
      await this.loadPersistedForm();
      
      // Setup auto-save
      if (this.ui.autoSaveEnabled) {
        this.setupAutoSave();
      }
      
      // Load piece size options
      this.loadPieceSizeOptions();
      
      // Initial validation
      this.validateForm();
    },
    
    // ============================================
    // Form Management
    // ============================================
    
    async loadPersistedForm() {
      const savedForm = StorageService.loadTorrentForm();
      if (savedForm) {
        // Merge saved data with current form
        Object.assign(this.form, savedForm);
        
        // Re-validate path if it exists
        if (this.form.path) {
          await this.validatePath();
        }
        
        // Re-validate trackers if they exist
        if (this.form.trackerUrls) {
          this.validateTrackers();
        }
        
        console.log('📋 Loaded persisted form data');
      }
    },
    
    setupAutoSave() {
      const debouncedSave = debounce(() => {
        if (this.ui.autoSaveEnabled) {
          StorageService.saveTorrentForm(this.form);
        }
      }, 1000);
      
      // Watch for form changes
      this.$watch('form', debouncedSave, { deep: true });
    },
    
    clearForm() {
      // Reset form to defaults
      this.form = {
        path: '',
        pieceSizeBytes: 0,
        pieceSizeMode: 'auto',
        privateTorrent: false,
        startSeeding: true,
        trackerUrls: '',
        webSeeds: '',
        comment: '',
        source: ''
      };
      
      // Reset component state
      this.pathData = {
        isValid: false,
        exists: false,
        totalSize: 0,
        fileCount: 0,
        directoryCount: 0,
        isScanning: false,
        error: null
      };
      
      this.pieceData = {
        isCalculating: false,
        recommendedSize: 0,
        pieceCount: 0,
        efficiency: 0,
        wastedSpace: 0,
        options: []
      };
      
      this.trackerData = {
        isValidating: false,
        isValid: false,
        tiers: [],
        trackerCount: 0,
        errors: [],
        warnings: []
      };
      
      // Clear persisted data
      StorageService.clearTorrentForm();
      
      console.log('🗑️ Form cleared');
    },

    // ============================================
    // Path Management
    // ============================================
    
    async validatePath() {
      if (!this.form.path) {
        this.pathData = { ...this.pathData, isValid: false, error: 'Path is required' };
        return;
      }
      
      const pathValidation = ValidationService.validatePath(this.form.path);
      if (!pathValidation.isValid) {
        this.pathData = { ...this.pathData, isValid: false, error: pathValidation.error };
        return;
      }
      
      // Scan path via API
      await this.scanPath();
    },
    
    async scanPath() {
      if (!this.form.path || this.pathData.isScanning) return;
      
      this.pathData.isScanning = true;
      this.pathData.error = null;
      
      try {
        const result = await apiClient.analyzeQbittorrentPath(this.form.path, {
          includeSize: true,
          recursive: true,
          maxItems: 1000
        });
        
        this.pathData = {
          ...this.pathData,
          isValid: true,
          exists: true,
          totalSize: result.totalSize || 0,
          fileCount: result.fileCount || 0,
          directoryCount: result.directoryCount || 0,
          error: null
        };
        
        // Add to recent paths
        StorageService.addRecentPath(this.form.path);
        
        // Auto-calculate piece size if in auto mode
        if (this.form.pieceSizeMode === 'auto' && this.pathData.totalSize > 0) {
          await this.calculatePieces();
        }
        
        console.log('📁 Path scanned successfully:', result);
        
      } catch (error) {
        this.pathData = {
          ...this.pathData,
          isValid: false,
          error: error.message || 'Failed to scan path'
        };
        console.error('❌ Path scan failed:', error);
      } finally {
        this.pathData.isScanning = false;
      }
    },

    // ============================================
    // Piece Size Management
    // ============================================
    
    loadPieceSizeOptions() {
      const options = [];
      for (let i = 14; i <= 24; i++) { // 2^14 (16KB) to 2^24 (16MB)
        const size = Math.pow(2, i);
        options.push({
          value: size,
          label: formatPieceSize(size)
        });
      }
      this.pieceData.options = options;
    },
    
    async calculatePieces() {
      if (!this.form.path || this.pieceData.isCalculating) return;
      
      this.pieceData.isCalculating = true;
      
      try {
        const result = await apiClient.calculatePieces(this.form.path, 2500);
        
        this.pieceData = {
          ...this.pieceData,
          recommendedSize: result.recommendedPieceSize,
          pieceCount: result.totalPieces,
          efficiency: result.efficiency || 0,
          wastedSpace: result.wastedBytes || 0
        };
        
        // Update form with recommended size if in auto mode
        if (this.form.pieceSizeMode === 'auto') {
          this.form.pieceSizeBytes = result.recommendedPieceSize;
        }
        
        console.log('⚙️ Piece size calculated:', result);
        
      } catch (error) {
        console.error('❌ Piece calculation failed:', error);
        // Fallback to manual calculation
        if (this.pathData.totalSize > 0) {
          const fallbackSize = this.calculateFallbackPieceSize(this.pathData.totalSize);
          this.form.pieceSizeBytes = fallbackSize;
          this.pieceData.recommendedSize = fallbackSize;
        }
      } finally {
        this.pieceData.isCalculating = false;
      }
    },
    
    calculateFallbackPieceSize(totalSize) {
      const targetPieces = 2500;
      const pieceSize = Math.max(16384, Math.pow(2, Math.ceil(Math.log2(totalSize / targetPieces))));
      return Math.min(pieceSize, 16777216); // Cap at 16MB
    },
    
    onPieceSizeModeChange() {
      if (this.form.pieceSizeMode === 'auto' && this.pathData.totalSize > 0) {
        this.calculatePieces();
      }
    },
    
    onManualPieceSizeChange() {
      if (this.form.pieceSizeMode === 'manual') {
        // Recalculate efficiency for manual size
        this.calculateEfficiencyForSize(this.form.pieceSizeBytes);
      }
    },
    
    calculateEfficiencyForSize(pieceSize) {
      if (this.pathData.totalSize > 0 && pieceSize > 0) {
        const totalPieces = Math.ceil(this.pathData.totalSize / pieceSize);
        const wastedBytes = (totalPieces * pieceSize) - this.pathData.totalSize;
        const efficiency = ((this.pathData.totalSize / (totalPieces * pieceSize)) * 100);
        
        this.pieceData.pieceCount = totalPieces;
        this.pieceData.efficiency = efficiency;
        this.pieceData.wastedSpace = wastedBytes;
      }
    },

    // ============================================
    // Tracker Management
    // ============================================
    
    validateTrackers() {
      this.trackerData.isValidating = true;
      
      const result = ValidationService.validateTrackers(this.form.trackerUrls);
      
      this.trackerData = {
        ...this.trackerData,
        isValid: result.isValid,
        tiers: result.tiers,
        trackerCount: result.trackerCount,
        errors: result.error ? [result.error] : [],
        warnings: result.warnings || [],
        isValidating: false
      };
      
      // Update overall validation
      this.validateForm();
    },
    
    loadTrackerPreset(preset) {
      this.form.trackerUrls = preset.trackerUrls;
      this.validateTrackers();
    },

    // ============================================
    // Form Validation
    // ============================================
    
    validateForm() {
      const summary = ValidationService.getValidationSummary(this.form);
      
      this.validation = {
        errors: summary.errors,
        warnings: summary.warnings,
        isValid: summary.isValid && this.pathData.isValid && this.trackerData.isValid
      };
    },

    // ============================================
    // Torrent Creation
    // ============================================
    
    async createTorrent() {
      if (!this.canCreate) return;
      
      this.progress.isCreating = true;
      this.progress.error = null;
      this.progress.result = null;
      
      try {
        const result = await apiClient.createTorrent(this.form);
        
        this.progress.result = result;
        this.progress.isCreating = false;
        
        console.log('✅ Torrent created successfully:', result);
        
        // Clear form after successful creation
        if (result.success) {
          this.clearForm();
        }
        
      } catch (error) {
        this.progress.error = error.message || 'Torrent creation failed';
        this.progress.isCreating = false;
        console.error('❌ Torrent creation failed:', error);
      }
    },

    // ============================================
    // Event Handlers
    // ============================================
    
    onPathChange() {
      // Debounced path validation
      if (this.pathValidationTimeout) {
        clearTimeout(this.pathValidationTimeout);
      }
      
      this.pathValidationTimeout = setTimeout(() => {
        this.validatePath();
      }, 500);
    },
    
    onTrackerChange() {
      // Debounced tracker validation
      if (this.trackerValidationTimeout) {
        clearTimeout(this.trackerValidationTimeout);
      }
      
      this.trackerValidationTimeout = setTimeout(() => {
        this.validateTrackers();
      }, 300);
    },
    
    onPrivateToggle() {
      // Show warning about source field for private torrents
      if (this.form.privateTorrent && !this.form.source.trim()) {
        this.validation.warnings.push('Private torrents should include a source for cross-seeding');
      }
      this.validateForm();
    }
  };
}

// Register the component with Alpine.js
document.addEventListener('alpine:init', () => {
  Alpine.data('torrentCreator', TorrentCreator);
});
