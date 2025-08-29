/**
 * Utility Functions
 * Common helper functions used throughout the application
 */

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format piece size with appropriate unit
 */
export function formatPieceSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${bytes / 1024} KB`;
  return `${bytes / (1024 * 1024)} MB`;
}

/**
 * Format number with thousand separators
 */
export function formatNumber(num) {
  return new Intl.NumberFormat().format(num);
}

/**
 * Format percentage with specified decimal places
 */
export function formatPercentage(value, decimals = 1) {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Debounce function calls
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function calls
 */
export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Deep clone an object
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime());
  if (obj instanceof Array) return obj.map(item => deepClone(item));
  
  const clonedObj = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      clonedObj[key] = deepClone(obj[key]);
    }
  }
  return clonedObj;
}

/**
 * Validate URL format
 */
export function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

/**
 * Validate file path format
 */
export function isValidPath(path) {
  if (!path || typeof path !== 'string') return false;
  
  // Basic path validation - starts with / for absolute paths
  return path.startsWith('/') && path.length > 1;
}

/**
 * Extract filename from path
 */
export function getFilenameFromPath(path) {
  if (!path) return '';
  return path.split('/').pop() || '';
}

/**
 * Extract directory from path
 */
export function getDirectoryFromPath(path) {
  if (!path) return '';
  const parts = path.split('/');
  parts.pop(); // Remove filename
  return parts.join('/') || '/';
}

/**
 * Generate random ID
 */
export function generateId(length = 8) {
  return Math.random().toString(36).substring(2, length + 2);
}

/**
 * Sleep/delay function
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Parse tracker text into tiers
 */
export function parseTrackerTiers(trackerText) {
  if (!trackerText || typeof trackerText !== 'string') return [];
  
  const lines = trackerText.split('\n').map(line => line.trim());
  const tiers = [];
  let currentTier = [];
  
  for (const line of lines) {
    if (line === '') {
      // Empty line indicates new tier
      if (currentTier.length > 0) {
        tiers.push([...currentTier]);
        currentTier = [];
      }
    } else if (isValidUrl(line)) {
      currentTier.push(line);
    }
  }
  
  // Add the last tier if it has content
  if (currentTier.length > 0) {
    tiers.push(currentTier);
  }
  
  return tiers;
}

/**
 * Format tracker tiers back to text
 */
export function formatTrackerTiers(tiers) {
  if (!Array.isArray(tiers)) return '';
  
  return tiers.map(tier => tier.join('\n')).join('\n\n');
}

/**
 * Calculate optimal piece size
 */
export function calculateOptimalPieceSize(totalSize, targetPieces = 2500) {
  const pieceSize = Math.max(16384, Math.pow(2, Math.ceil(Math.log2(totalSize / targetPieces))));
  return Math.min(pieceSize, 16777216); // Cap at 16MB
}

/**
 * Validate piece size
 */
export function isValidPieceSize(size) {
  // Must be power of 2, between 16KB and 16MB
  return size >= 16384 && 
         size <= 16777216 && 
         (size & (size - 1)) === 0;
}

/**
 * Get available piece sizes
 */
export function getPieceSizeOptions() {
  const options = [];
  for (let i = 14; i <= 24; i++) { // 2^14 (16KB) to 2^24 (16MB)
    const size = Math.pow(2, i);
    options.push({
      value: size,
      label: formatPieceSize(size),
    });
  }
  return options;
}

/**
 * Show notification (can be extended with toast library)
 */
export function showNotification(message, type = 'info') {
  console.log(`[${type.toUpperCase()}] ${message}`);
  // TODO: Integrate with toast notification library
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showNotification('Copied to clipboard', 'success');
    return true;
  } catch (err) {
    console.error('Failed to copy to clipboard:', err);
    showNotification('Failed to copy to clipboard', 'error');
    return false;
  }
}

/**
 * Download text as file
 */
export function downloadTextAsFile(text, filename) {
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
