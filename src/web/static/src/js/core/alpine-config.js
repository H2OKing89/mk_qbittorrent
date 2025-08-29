/**
 * Alpine.js Configuration and Setup
 * Initializes Alpine.js with plugins and global configurations
 */
import Alpine from 'alpinejs';
import focus from '@alpinejs/focus';
import collapse from '@alpinejs/collapse';
import intersect from '@alpinejs/intersect';
import persist from '@alpinejs/persist';
import autoAnimate from '@formkit/auto-animate';

// Register Alpine.js plugins
Alpine.plugin(focus);
Alpine.plugin(collapse);
Alpine.plugin(intersect);
Alpine.plugin(persist);

// Register Auto-Animate plugin
Alpine.plugin(autoAnimate);

// Global Alpine.js configurations
Alpine.data('autoAnimate', () => ({
  init() {
    autoAnimate(this.$el);
  },
}));

// Global error handler
window.addEventListener('alpine:init', () => {
  console.log('🚀 Alpine.js initialized with plugins');
});

// Start Alpine.js
Alpine.start();

// Export for module usage
export default Alpine;
