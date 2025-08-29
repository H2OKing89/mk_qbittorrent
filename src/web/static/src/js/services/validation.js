/**
 * Form Validation Service using Zod
 * Provides comprehensive validation for torrent creation forms
 */
import { z } from 'zod';

// ============================================
// Validation Schemas
// ============================================

export const TorrentCreationSchema = z.object({
  path: z.string()
    .min(1, 'Path is required')
    .refine(path => path.startsWith('/'), 'Path must be absolute (start with /)'),
  
  pieceSizeBytes: z.number()
    .min(16384, 'Piece size must be at least 16 KB')
    .max(16777216, 'Piece size must not exceed 16 MB')
    .refine(size => (size & (size - 1)) === 0, 'Piece size must be a power of 2'),
  
  pieceSizeMode: z.enum(['auto', 'manual']).default('auto'),
  
  privateTorrent: z.boolean().default(false),
  
  startSeeding: z.boolean().default(true),
  
  trackerUrls: z.string()
    .min(1, 'At least one tracker is required')
    .transform(text => text.trim()),
  
  webSeeds: z.string().optional().default(''),
  
  comment: z.string().optional().default(''),
  
  source: z.string().optional().default('')
});

export const TrackerValidationSchema = z.array(
  z.string().url('Invalid tracker URL')
);

export const PathValidationSchema = z.object({
  path: z.string()
    .min(1, 'Path cannot be empty')
    .refine(path => path.startsWith('/'), 'Path must be absolute')
});

// ============================================
// Validation Service Class
// ============================================

export class ValidationService {
  /**
   * Validate complete torrent creation form
   */
  static validateTorrentForm(formData) {
    try {
      const validData = TorrentCreationSchema.parse(formData);
      return {
        success: true,
        data: validData,
        errors: {}
      };
    } catch (error) {
      if (error instanceof z.ZodError) {
        const fieldErrors = {};
        error.errors.forEach(err => {
          const field = err.path.join('.');
          fieldErrors[field] = err.message;
        });
        
        return {
          success: false,
          data: null,
          errors: fieldErrors
        };
      }
      
      return {
        success: false,
        data: null,
        errors: { general: 'Validation failed' }
      };
    }
  }

  /**
   * Validate individual field
   */
  static validateField(fieldName, value, schema = TorrentCreationSchema) {
    try {
      const fieldSchema = schema.shape[fieldName];
      if (!fieldSchema) {
        return { isValid: false, error: 'Unknown field' };
      }
      
      fieldSchema.parse(value);
      return { isValid: true, error: null };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          isValid: false,
          error: error.errors[0]?.message || 'Invalid value'
        };
      }
      
      return { isValid: false, error: 'Validation error' };
    }
  }

  /**
   * Validate path format
   */
  static validatePath(path) {
    try {
      PathValidationSchema.parse({ path });
      return { isValid: true, error: null };
    } catch (error) {
      return {
        isValid: false,
        error: error.errors[0]?.message || 'Invalid path'
      };
    }
  }

  /**
   * Parse and validate tracker URLs
   */
  static validateTrackers(trackerText) {
    if (!trackerText || typeof trackerText !== 'string') {
      return {
        isValid: false,
        error: 'Tracker text is required',
        tiers: [],
        trackerCount: 0
      };
    }

    try {
      const tiers = this.parseTrackerTiers(trackerText);
      
      if (tiers.length === 0) {
        return {
          isValid: false,
          error: 'No valid trackers found',
          tiers: [],
          trackerCount: 0
        };
      }

      // Validate each URL in each tier
      const validationErrors = [];
      const validatedTiers = [];

      tiers.forEach((tier, tierIndex) => {
        const validatedTier = [];
        
        tier.forEach((url, urlIndex) => {
          try {
            new URL(url); // Basic URL validation
            validatedTier.push(url);
          } catch {
            validationErrors.push(`Tier ${tierIndex + 1}, URL ${urlIndex + 1}: Invalid URL format`);
          }
        });
        
        if (validatedTier.length > 0) {
          validatedTiers.push(validatedTier);
        }
      });

      const totalTrackers = validatedTiers.reduce((sum, tier) => sum + tier.length, 0);

      return {
        isValid: validationErrors.length === 0,
        error: validationErrors.length > 0 ? validationErrors.join('; ') : null,
        tiers: validatedTiers,
        trackerCount: totalTrackers,
        warnings: validationErrors.length > 0 ? [`${validationErrors.length} invalid URLs found`] : []
      };

    } catch (error) {
      return {
        isValid: false,
        error: 'Failed to parse tracker text',
        tiers: [],
        trackerCount: 0
      };
    }
  }

  /**
   * Parse tracker text into tiers
   */
  static parseTrackerTiers(trackerText) {
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
      } else if (line.startsWith('http://') || line.startsWith('https://') || line.startsWith('udp://')) {
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
   * Validate piece size
   */
  static validatePieceSize(size) {
    if (typeof size !== 'number' || isNaN(size)) {
      return { isValid: false, error: 'Piece size must be a number' };
    }

    if (size < 16384) {
      return { isValid: false, error: 'Piece size must be at least 16 KB' };
    }

    if (size > 16777216) {
      return { isValid: false, error: 'Piece size must not exceed 16 MB' };
    }

    if ((size & (size - 1)) !== 0) {
      return { isValid: false, error: 'Piece size must be a power of 2' };
    }

    return { isValid: true, error: null };
  }

  /**
   * Get validation summary for form
   */
  static getValidationSummary(formData) {
    const result = this.validateTorrentForm(formData);
    const trackerValidation = this.validateTrackers(formData.trackerUrls || '');
    
    const errors = { ...result.errors };
    const warnings = [];

    // Add tracker warnings
    if (trackerValidation.warnings && trackerValidation.warnings.length > 0) {
      warnings.push(...trackerValidation.warnings);
    }

    // Check for common issues
    if (formData.privateTorrent && (!formData.source || formData.source.trim() === '')) {
      warnings.push('Private torrents should include a source for cross-seeding');
    }

    if (trackerValidation.trackerCount === 1) {
      warnings.push('Consider adding backup trackers for better availability');
    }

    return {
      isValid: result.success && trackerValidation.isValid,
      errors,
      warnings,
      trackerInfo: {
        tierCount: trackerValidation.tiers.length,
        trackerCount: trackerValidation.trackerCount
      }
    };
  }
}

// Export default instance for convenience
export default ValidationService;
