# 🏗️ Web Directory Structure & Modularity Guide

> **Goal**: Design a **scalable, maintainable** web architecture that supports **professional development workflows** and **advanced JavaScript packages**.

---

## 🎯 **Current vs. Proposed Structure**

### **📁 Current Structure**
```
src/web/
├── app.py                 # FastAPI application
├── static/
│   └── style.css         # Single CSS file
├── templates/
│   └── torrent_creator.html  # Single HTML template
└── __pycache__/
```

### **🚀 Proposed Modular Structure**
```
src/web/
├── app.py                      # FastAPI application (enhanced)
├── package.json               # Package management
├── vite.config.js             # Build configuration
├── tailwind.config.js         # Tailwind configuration
├── .eslintrc.js              # Linting rules
├── .prettierrc               # Code formatting
├── static/
│   ├── src/                   # Source files (development)
│   │   ├── js/
│   │   │   ├── core/
│   │   │   │   ├── alpine-config.js
│   │   │   │   ├── api-client.js
│   │   │   │   ├── utils.js
│   │   │   │   ├── constants.js
│   │   │   │   └── types.js
│   │   │   ├── components/
│   │   │   │   ├── TorrentCreator.js
│   │   │   │   ├── PathSelector.js
│   │   │   │   ├── SettingsPanel.js
│   │   │   │   ├── TrackerEditor.js
│   │   │   │   ├── ProgressMonitor.js
│   │   │   │   ├── FileBrowser.js
│   │   │   │   └── AdvancedSettings.js
│   │   │   ├── services/
│   │   │   │   ├── websocket.js
│   │   │   │   ├── validation.js
│   │   │   │   ├── storage.js
│   │   │   │   ├── analytics.js
│   │   │   │   └── error-handler.js
│   │   │   ├── stores/
│   │   │   │   ├── torrent-store.js
│   │   │   │   ├── settings-store.js
│   │   │   │   └── ui-store.js
│   │   │   └── main.js
│   │   ├── css/
│   │   │   ├── base/
│   │   │   │   ├── reset.css
│   │   │   │   ├── typography.css
│   │   │   │   └── variables.css
│   │   │   ├── components/
│   │   │   │   ├── buttons.css
│   │   │   │   ├── forms.css
│   │   │   │   ├── cards.css
│   │   │   │   ├── modals.css
│   │   │   │   └── progress.css
│   │   │   ├── layouts/
│   │   │   │   ├── header.css
│   │   │   │   ├── main.css
│   │   │   │   ├── footer.css
│   │   │   │   └── responsive.css
│   │   │   ├── themes/
│   │   │   │   ├── qbittorrent-dark.css
│   │   │   │   └── qbittorrent-light.css
│   │   │   └── main.css
│   │   └── assets/
│   │       ├── icons/
│   │       │   ├── custom/
│   │       │   └── vendors/
│   │       ├── animations/
│   │       │   ├── loading.json
│   │       │   ├── success.json
│   │       │   └── error.json
│   │       ├── images/
│   │       └── fonts/
│   └── dist/                  # Built files (production)
│       ├── assets/
│       │   ├── js/
│       │   ├── css/
│       │   └── images/
│       └── manifest.json
├── templates/
│   ├── base.html             # Base template
│   ├── layouts/
│   │   ├── app.html          # Application layout
│   │   └── minimal.html      # Minimal layout
│   ├── pages/
│   │   ├── torrent-creator.html
│   │   ├── settings.html
│   │   └── help.html
│   ├── components/
│   │   ├── header.html
│   │   ├── footer.html
│   │   ├── navigation.html
│   │   └── modals/
│   │       ├── file-browser.html
│   │       └── settings-modal.html
│   └── macros/
│       ├── forms.html
│       ├── buttons.html
│       └── progress.html
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── torrent.py        # Torrent-related endpoints
│   │   ├── qbittorrent.py    # qBittorrent API endpoints
│   │   ├── settings.py       # Settings endpoints
│   │   └── websocket.py      # WebSocket handlers
│   ├── models/
│   │   ├── requests.py       # Pydantic request models
│   │   ├── responses.py      # Pydantic response models
│   │   └── validation.py     # Validation schemas
│   ├── middleware/
│   │   ├── cors.py
│   │   ├── auth.py
│   │   └── rate_limit.py
│   └── utils/
│       ├── exceptions.py
│       └── helpers.py
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 🧩 **Component Architecture**

### **🏗️ Core Components**

#### **1. TorrentCreator.js** (Main Component)
```javascript
/**
 * Main Alpine.js component for torrent creation
 * Coordinates all sub-components and manages global state
 */
export function TorrentCreator() {
  return {
    // Global State
    form: {
      path: '',
      totalBytes: null,
      fileCount: null,
      pieceSizeMode: 'auto',
      pieceSizeBytes: null,
      targetPieces: 2500,
      privateTorrent: true,
      startSeeding: false,
      trackerUrls: '',
      webSeeds: '',
      comment: '',
      source: ''
    },
    
    // UI State
    ui: {
      currentStep: 'path-selection',
      isProcessing: false,
      showAdvanced: false,
      errors: {},
      warnings: []
    },
    
    // Progress State
    progress: {
      phase: 'idle',
      percent: 0,
      eta: null,
      currentFile: null
    },
    
    // Computed Properties
    get canCreate() {
      return this.form.path && 
             this.form.trackerUrls.trim() && 
             this.form.pieceSizeBytes;
    },
    
    get validationErrors() {
      return TorrentValidation.validate(this.form);
    },
    
    // Methods
    async init() {
      await this.loadPersistedState();
      this.setupWebSocket();
      this.setupAutoSave();
    },
    
    async createTorrent() {
      // Implementation
    },
    
    // Event Handlers
    onPathChange(path) {
      // Implementation
    },
    
    onProgressUpdate(data) {
      // Implementation
    }
  }
}
```

#### **2. PathSelector.js** (File Selection)
```javascript
/**
 * Handles file/folder selection and path validation
 */
export function PathSelector() {
  return {
    currentPath: '',
    browserOpen: false,
    recentPaths: [],
    suggestions: [],
    
    async browsePath(type = 'folder') {
      // Open file browser modal
    },
    
    async validatePath(path) {
      // API call to validate path
    },
    
    async scanPath(path) {
      // Scan path for size and file count
    }
  }
}
```

#### **3. SettingsPanel.js** (Piece Size & Privacy)
```javascript
/**
 * Manages piece size calculation and privacy settings
 */
export function SettingsPanel() {
  return {
    pieceSizeOptions: [
      { value: 16384, label: '16 KiB' },
      { value: 32768, label: '32 KiB' },
      // ... more options
    ],
    
    async calculatePieces() {
      // API call to calculate optimal piece size
    },
    
    onPieceSizeModeChange(mode) {
      // Handle auto/manual toggle
    },
    
    onPrivateToggle(isPrivate) {
      // Handle private torrent warnings
    }
  }
}
```

#### **4. TrackerEditor.js** (Multi-tier Trackers)
```javascript
/**
 * Advanced tracker management with tier support
 */
export function TrackerEditor() {
  return {
    trackerText: '',
    trackerTiers: [],
    validationResults: [],
    presets: [],
    
    parseTrackers() {
      // Parse multiline tracker input into tiers
    },
    
    validateTrackers() {
      // Real-time URL validation
    },
    
    addPreset(presetName) {
      // Add tracker preset
    },
    
    exportTrackers() {
      // Export tracker configuration
    }
  }
}
```

#### **5. ProgressMonitor.js** (Real-time Progress)
```javascript
/**
 * Real-time progress monitoring with WebSocket
 */
export function ProgressMonitor() {
  return {
    socket: null,
    jobId: null,
    phases: ['scanning', 'hashing', 'finalizing'],
    currentPhase: 0,
    
    connectWebSocket() {
      // Setup WebSocket connection
    },
    
    onProgressUpdate(data) {
      // Handle progress events
    },
    
    onComplete(result) {
      // Handle completion
    },
    
    onError(error) {
      // Handle errors
    }
  }
}
```

### **🔧 Service Layer**

#### **api-client.js** (Centralized API)
```javascript
/**
 * Centralized API client with error handling and caching
 */
class ApiClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.cache = new Map();
  }
  
  async get(endpoint, options = {}) {
    // GET request with caching
  }
  
  async post(endpoint, data, options = {}) {
    // POST request with error handling
  }
  
  async analyzeQbittorrentPath(path, options = {}) {
    return this.post('/qbittorrent/analyze', {
      path,
      includeSize: true,
      recursive: true,
      ...options
    });
  }
  
  async calculatePieces(path, targetPieces = 2500) {
    return this.post('/qbittorrent/calculate-pieces', {
      path,
      targetPieces
    });
  }
  
  async createTorrent(formData) {
    return this.post('/create-enhanced', formData);
  }
}

export const apiClient = new ApiClient();
```

#### **validation.js** (Form Validation)
```javascript
/**
 * Zod-based validation schemas
 */
import { z } from 'zod';

export const TorrentSchema = z.object({
  path: z.string().min(1, 'Path is required'),
  pieceSizeBytes: z.number().min(16384).max(16777216),
  privateTorrent: z.boolean(),
  startSeeding: z.boolean(),
  trackerUrls: z.string().min(1, 'At least one tracker required'),
  webSeeds: z.string().optional(),
  comment: z.string().optional(),
  source: z.string().optional()
});

export const TrackerTierSchema = z.array(
  z.string().url('Invalid tracker URL')
);

export class TorrentValidation {
  static validate(formData) {
    try {
      TorrentSchema.parse(formData);
      return { valid: true, errors: {} };
    } catch (error) {
      return {
        valid: false,
        errors: error.flatten().fieldErrors
      };
    }
  }
  
  static validateTrackers(trackerText) {
    // Parse and validate tracker tiers
  }
}
```

#### **storage.js** (State Persistence)
```javascript
/**
 * localStorage management for form state
 */
export class TorrentStorage {
  static STORAGE_KEY = 'torrent-creator-state';
  
  static save(state) {
    localStorage.setItem(
      this.STORAGE_KEY,
      JSON.stringify({
        ...state,
        timestamp: Date.now()
      })
    );
  }
  
  static load() {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (!stored) return null;
    
    const data = JSON.parse(stored);
    
    // Check if data is not too old (24 hours)
    if (Date.now() - data.timestamp > 24 * 60 * 60 * 1000) {
      this.clear();
      return null;
    }
    
    return data;
  }
  
  static clear() {
    localStorage.removeItem(this.STORAGE_KEY);
  }
}
```

#### **websocket.js** (Real-time Communication)
```javascript
/**
 * WebSocket service for real-time progress updates
 */
import { io } from 'socket.io-client';

export class TorrentWebSocket {
  constructor() {
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }
  
  connect() {
    this.socket = io('/torrent-progress');
    
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });
    
    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.reconnect();
    });
    
    this.socket.on('progress', (data) => {
      this.onProgress?.(data);
    });
    
    this.socket.on('complete', (data) => {
      this.onComplete?.(data);
    });
    
    this.socket.on('error', (error) => {
      this.onError?.(error);
    });
  }
  
  reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, 1000 * Math.pow(2, this.reconnectAttempts));
    }
  }
  
  joinJob(jobId) {
    this.socket?.emit('join-job', jobId);
  }
  
  leaveJob(jobId) {
    this.socket?.emit('leave-job', jobId);
  }
  
  disconnect() {
    this.socket?.disconnect();
  }
}
```

---

## 🎨 **CSS Architecture (Modular)**

### **main.css** (Entry Point)
```css
/* Import order matters for cascade */
@import './base/reset.css';
@import './base/variables.css';
@import './base/typography.css';

@import './components/buttons.css';
@import './components/forms.css';
@import './components/cards.css';
@import './components/modals.css';
@import './components/progress.css';

@import './layouts/header.css';
@import './layouts/main.css';
@import './layouts/footer.css';
@import './layouts/responsive.css';

@import './themes/qbittorrent-dark.css';
```

### **base/variables.css** (Design Tokens)
```css
:root {
  /* Colors */
  --qbit-bg-primary: #2b2b2b;
  --qbit-bg-secondary: #3c3c3c;
  --qbit-bg-tertiary: #4a4a4a;
  --qbit-accent: #3daee9;
  --qbit-accent-hover: #2980b9;
  --qbit-success: #27ae60;
  --qbit-warning: #f39c12;
  --qbit-error: #e74c3c;
  
  /* Typography */
  --qbit-font-family: 'Inter', system-ui, sans-serif;
  --qbit-font-size-base: 1rem;
  --qbit-font-size-sm: 0.875rem;
  --qbit-font-size-lg: 1.125rem;
  --qbit-font-size-xl: 1.25rem;
  
  /* Spacing */
  --qbit-space-xs: 0.25rem;
  --qbit-space-sm: 0.5rem;
  --qbit-space-md: 1rem;
  --qbit-space-lg: 1.5rem;
  --qbit-space-xl: 2rem;
  
  /* Border Radius */
  --qbit-radius-sm: 0.25rem;
  --qbit-radius-md: 0.375rem;
  --qbit-radius-lg: 0.5rem;
  
  /* Shadows */
  --qbit-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --qbit-shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --qbit-shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --qbit-transition-fast: 150ms ease;
  --qbit-transition-base: 300ms ease;
  --qbit-transition-slow: 500ms ease;
}
```

### **components/cards.css** (Card Components)
```css
.qbit-card {
  background-color: var(--qbit-bg-secondary);
  border: 1px solid color-mix(in srgb, var(--qbit-accent) 20%, transparent);
  border-radius: var(--qbit-radius-lg);
  box-shadow: var(--qbit-shadow-lg);
  padding: var(--qbit-space-lg);
  transition: all var(--qbit-transition-base);
}

.qbit-card:hover {
  border-color: color-mix(in srgb, var(--qbit-accent) 50%, transparent);
  box-shadow: var(--qbit-shadow-xl);
  transform: translateY(-2px);
}

.qbit-card-header {
  display: flex;
  align-items: center;
  gap: var(--qbit-space-sm);
  margin-bottom: var(--qbit-space-lg);
}

.qbit-card-title {
  font-size: var(--qbit-font-size-lg);
  font-weight: 600;
  color: var(--qbit-text-primary);
}

.qbit-card-content {
  /* Content styles */
}
```

---

## 🔧 **Build Configuration**

### **vite.config.js**
```javascript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname, 'static/src'),
  base: '/static/',
  build: {
    outDir: resolve(__dirname, 'static/dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'static/src/main.js')
      },
      output: {
        entryFileNames: 'assets/js/[name].[hash].js',
        chunkFileNames: 'assets/js/[name].[hash].js',
        assetFileNames: 'assets/[ext]/[name].[hash].[ext]'
      }
    },
    sourcemap: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8094',
        changeOrigin: true
      }
    },
    watch: {
      include: ['static/src/**', 'templates/**']
    }
  },
  css: {
    postcss: {
      plugins: [
        require('tailwindcss'),
        require('autoprefixer')
      ]
    }
  }
});
```

### **package.json** (Scripts)
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "watch": "vite build --watch",
    "clean": "rm -rf static/dist",
    "lint": "eslint static/src --ext .js",
    "lint:fix": "eslint static/src --ext .js --fix",
    "format": "prettier --write static/src templates",
    "type-check": "tsc --noEmit",
    "analyze": "vite-bundle-analyzer static/dist"
  }
}
```

---

## 🚀 **Migration Steps**

### **Phase 1: Setup Structure (2-3 hours)**
1. ✅ Create new directory structure
2. ✅ Setup package.json and Vite config
3. ✅ Move existing files to new structure
4. ✅ Configure build process

### **Phase 2: Modularize Components (3-4 hours)**
1. ✅ Split TorrentCreator into modules
2. ✅ Create service layer (API, validation, storage)
3. ✅ Implement CSS architecture
4. ✅ Setup development workflow

### **Phase 3: Advanced Features (4-5 hours)**
1. ✅ Add WebSocket service
2. ✅ Implement file browser modal
3. ✅ Add progress visualization
4. ✅ Setup error handling

### **Phase 4: Testing & Polish (2-3 hours)**
1. ✅ Add unit tests
2. ✅ Setup E2E testing
3. ✅ Performance optimization
4. ✅ Documentation

---

**This modular architecture will make our codebase:**
- 🧩 **Maintainable** - Clear separation of concerns
- ⚡ **Scalable** - Easy to add new features
- 🔧 **Testable** - Isolated components and services
- 🚀 **Professional** - Industry-standard structure

**Ready to implement the new structure?** 🎯
