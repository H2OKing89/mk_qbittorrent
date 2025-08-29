/**
 * Main Entry Point for the Torrent Creator Application
 * Initializes the Alpine.js application with components and services
 */

// Import Alpine.js and plugins
import Alpine from 'alpinejs';
import collapse from '@alpinejs/collapse';
import persist from '@alpinejs/persist';
import focus from '@alpinejs/focus';

// Import our component
import { TorrentCreator } from './components/TorrentCreator.js';

// Initialize Alpine plugins BEFORE Alpine.start()
Alpine.plugin(collapse);
Alpine.plugin(persist);
Alpine.plugin(focus);

// Register our component
Alpine.data('torrentCreator', TorrentCreator);

// Store Alpine on window for debugging
window.Alpine = Alpine;

// Global Alpine stores
Alpine.store('app', {
  version: '1.0.0',
  theme: 'dark',
  debug: true
});

// Start Alpine
Alpine.start();

console.log('✅ Torrent Creator initialized');
