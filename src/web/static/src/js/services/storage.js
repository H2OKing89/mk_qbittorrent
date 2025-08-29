/**
 * Local Storage Service
 * Handles persistent storage of form state and user preferences
 */

export class StorageService {
  static STORAGE_KEYS = {
    TORRENT_FORM: 'qbit-torrent-creator-form',
    USER_PREFERENCES: 'qbit-user-preferences',
    RECENT_PATHS: 'qbit-recent-paths',
    TRACKER_PRESETS: 'qbit-tracker-presets'
  };

  /**
   * Save torrent form state
   */
  static saveTorrentForm(formData) {
    try {
      const dataToSave = {
        ...formData,
        timestamp: Date.now(),
        version: '1.0'
      };
      
      localStorage.setItem(
        this.STORAGE_KEYS.TORRENT_FORM,
        JSON.stringify(dataToSave)
      );
      
      return true;
    } catch (error) {
      console.error('Failed to save torrent form data:', error);
      return false;
    }
  }

  /**
   * Load torrent form state
   */
  static loadTorrentForm() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.TORRENT_FORM);
      if (!stored) return null;

      const data = JSON.parse(stored);
      
      // Check if data is too old (7 days)
      const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
      if (Date.now() - data.timestamp > maxAge) {
        this.clearTorrentForm();
        return null;
      }

      // Remove metadata before returning
      const { timestamp, version, ...formData } = data;
      return formData;
    } catch (error) {
      console.error('Failed to load torrent form data:', error);
      return null;
    }
  }

  /**
   * Clear torrent form state
   */
  static clearTorrentForm() {
    try {
      localStorage.removeItem(this.STORAGE_KEYS.TORRENT_FORM);
      return true;
    } catch (error) {
      console.error('Failed to clear torrent form data:', error);
      return false;
    }
  }

  /**
   * Save user preferences
   */
  static saveUserPreferences(preferences) {
    try {
      const dataToSave = {
        ...preferences,
        timestamp: Date.now(),
        version: '1.0'
      };
      
      localStorage.setItem(
        this.STORAGE_KEYS.USER_PREFERENCES,
        JSON.stringify(dataToSave)
      );
      
      return true;
    } catch (error) {
      console.error('Failed to save user preferences:', error);
      return false;
    }
  }

  /**
   * Load user preferences
   */
  static loadUserPreferences() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.USER_PREFERENCES);
      if (!stored) return this.getDefaultPreferences();

      const data = JSON.parse(stored);
      const { timestamp, version, ...preferences } = data;
      
      return {
        ...this.getDefaultPreferences(),
        ...preferences
      };
    } catch (error) {
      console.error('Failed to load user preferences:', error);
      return this.getDefaultPreferences();
    }
  }

  /**
   * Get default user preferences
   */
  static getDefaultPreferences() {
    return {
      theme: 'dark',
      autoSaveForm: true,
      showAdvancedOptions: false,
      defaultPieceSize: 'auto',
      rememberRecentPaths: true,
      maxRecentPaths: 10
    };
  }

  /**
   * Add path to recent paths
   */
  static addRecentPath(path) {
    try {
      const preferences = this.loadUserPreferences();
      if (!preferences.rememberRecentPaths) return false;

      let recentPaths = this.getRecentPaths();
      
      // Remove if already exists
      recentPaths = recentPaths.filter(p => p.path !== path);
      
      // Add to beginning
      recentPaths.unshift({
        path,
        timestamp: Date.now()
      });
      
      // Limit to max items
      recentPaths = recentPaths.slice(0, preferences.maxRecentPaths);
      
      localStorage.setItem(
        this.STORAGE_KEYS.RECENT_PATHS,
        JSON.stringify(recentPaths)
      );
      
      return true;
    } catch (error) {
      console.error('Failed to add recent path:', error);
      return false;
    }
  }

  /**
   * Get recent paths
   */
  static getRecentPaths() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.RECENT_PATHS);
      if (!stored) return [];

      const paths = JSON.parse(stored);
      
      // Filter out old paths (30 days)
      const maxAge = 30 * 24 * 60 * 60 * 1000;
      return paths.filter(p => Date.now() - p.timestamp < maxAge);
    } catch (error) {
      console.error('Failed to get recent paths:', error);
      return [];
    }
  }

  /**
   * Clear recent paths
   */
  static clearRecentPaths() {
    try {
      localStorage.removeItem(this.STORAGE_KEYS.RECENT_PATHS);
      return true;
    } catch (error) {
      console.error('Failed to clear recent paths:', error);
      return false;
    }
  }

  /**
   * Save tracker preset
   */
  static saveTrackerPreset(name, trackerUrls, description = '') {
    try {
      const presets = this.getTrackerPresets();
      
      // Remove existing preset with same name
      const filteredPresets = presets.filter(p => p.name !== name);
      
      // Add new preset
      filteredPresets.push({
        name,
        trackerUrls,
        description,
        timestamp: Date.now()
      });
      
      localStorage.setItem(
        this.STORAGE_KEYS.TRACKER_PRESETS,
        JSON.stringify(filteredPresets)
      );
      
      return true;
    } catch (error) {
      console.error('Failed to save tracker preset:', error);
      return false;
    }
  }

  /**
   * Get tracker presets
   */
  static getTrackerPresets() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEYS.TRACKER_PRESETS);
      if (!stored) return this.getDefaultTrackerPresets();

      const presets = JSON.parse(stored);
      return [...this.getDefaultTrackerPresets(), ...presets];
    } catch (error) {
      console.error('Failed to get tracker presets:', error);
      return this.getDefaultTrackerPresets();
    }
  }

  /**
   * Get default tracker presets
   */
  static getDefaultTrackerPresets() {
    return [
      {
        name: 'Public Trackers',
        description: 'Common public tracker list',
        trackerUrls: [
          'udp://tracker.opentrackr.org:1337/announce',
          'udp://tracker.openbittorrent.com:6969/announce',
          'udp://9.rarbg.to:2710/announce',
          'udp://tracker.coppersurfer.tk:6969/announce'
        ].join('\n\n'), // Empty line between tiers
        isDefault: true
      }
    ];
  }

  /**
   * Delete tracker preset
   */
  static deleteTrackerPreset(name) {
    try {
      const presets = this.getTrackerPresets();
      const filteredPresets = presets.filter(p => p.name !== name && !p.isDefault);
      
      localStorage.setItem(
        this.STORAGE_KEYS.TRACKER_PRESETS,
        JSON.stringify(filteredPresets)
      );
      
      return true;
    } catch (error) {
      console.error('Failed to delete tracker preset:', error);
      return false;
    }
  }

  /**
   * Get storage usage information
   */
  static getStorageInfo() {
    try {
      let totalSize = 0;
      const items = {};
      
      for (const key of Object.values(this.STORAGE_KEYS)) {
        const item = localStorage.getItem(key);
        if (item) {
          const size = new Blob([item]).size;
          items[key] = size;
          totalSize += size;
        }
      }
      
      return {
        totalSize,
        items,
        available: true
      };
    } catch (error) {
      console.error('Failed to get storage info:', error);
      return {
        totalSize: 0,
        items: {},
        available: false
      };
    }
  }

  /**
   * Clear all stored data
   */
  static clearAll() {
    try {
      for (const key of Object.values(this.STORAGE_KEYS)) {
        localStorage.removeItem(key);
      }
      return true;
    } catch (error) {
      console.error('Failed to clear all storage:', error);
      return false;
    }
  }

  /**
   * Check if localStorage is available
   */
  static isAvailable() {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch {
      return false;
    }
  }
}

// Export default instance
export default StorageService;
