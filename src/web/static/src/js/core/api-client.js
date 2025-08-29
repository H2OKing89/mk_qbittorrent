/**
 * Centralized API Client
 * Handles all HTTP requests with error handling, caching, and retry logic
 */

class ApiClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.cache = new Map();
    this.requestInterceptors = [];
    this.responseInterceptors = [];
  }

  /**
   * Generic HTTP request method
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Apply request interceptors
    for (const interceptor of this.requestInterceptors) {
      await interceptor(config);
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Apply response interceptors
      for (const interceptor of this.responseInterceptors) {
        await interceptor(data, response);
      }

      return data;
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  /**
   * GET request with caching support
   */
  async get(endpoint, options = {}) {
    const cacheKey = `GET:${endpoint}`;
    
    if (options.useCache && this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const data = await this.request(endpoint, {
      method: 'GET',
      ...options,
    });

    if (options.useCache) {
      this.cache.set(cacheKey, data);
    }

    return data;
  }

  /**
   * POST request
   */
  async post(endpoint, body = null, options = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : null,
      ...options,
    });
  }

  /**
   * PUT request
   */
  async put(endpoint, body = null, options = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : null,
      ...options,
    });
  }

  /**
   * DELETE request
   */
  async delete(endpoint, options = {}) {
    return this.request(endpoint, {
      method: 'DELETE',
      ...options,
    });
  }

  // ============================================
  // qBittorrent API Methods
  // ============================================

  /**
   * Analyze qBittorrent path
   */
  async analyzeQbittorrentPath(path, options = {}) {
    return this.post('/qbittorrent/analyze', {
      path,
      includeSize: options.includeSize ?? true,
      recursive: options.recursive ?? false,
      maxItems: options.maxItems ?? 1000,
    });
  }

  /**
   * Calculate optimal piece size
   */
  async calculatePieces(path, targetPieces = 2500) {
    return this.post('/qbittorrent/calculate-pieces', {
      path,
      targetPieces,
    });
  }

  /**
   * Browse qBittorrent directory
   */
  async browseQbittorrentPath(path) {
    return this.post('/qbittorrent/browse', { path });
  }

  /**
   * Get qBittorrent default paths
   */
  async getQbittorrentDefaultPaths() {
    return this.get('/qbittorrent/default-paths', { useCache: true });
  }

  /**
   * Validate tracker URLs
   */
  async validateTrackers(trackerUrls) {
    return this.post('/torrentcreator/validate-trackers', {
      trackerUrls,
    });
  }

  /**
   * Create torrent
   */
  async createTorrent(formData) {
    return this.post('/torrentcreator/create', formData);
  }

  /**
   * Get creation progress
   */
  async getCreationProgress(taskId) {
    return this.get(`/torrentcreator/progress/${taskId}`);
  }

  /**
   * Cancel torrent creation
   */
  async cancelCreation(taskId) {
    return this.post(`/torrentcreator/cancel/${taskId}`);
  }

  // ============================================
  // Utility Methods
  // ============================================

  /**
   * Clear all cached responses
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Add request interceptor
   */
  addRequestInterceptor(interceptor) {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Add response interceptor
   */
  addResponseInterceptor(interceptor) {
    this.responseInterceptors.push(interceptor);
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export { ApiClient };
