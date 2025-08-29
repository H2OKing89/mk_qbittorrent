# 🎨 Frontend Technology Stack & Design System

## **🎯 Core Technology Choices**

### **Primary Framework: Alpine.js** ✅
**Why Alpine.js?**
- ✅ **Lightweight** (15KB) - Perfect for torrent creator UI
- ✅ **No build step** - Simple deployment and debugging  
- ✅ **Progressive enhancement** - Works without JavaScript
- ✅ **Vue-like syntax** - Familiar reactive patterns
- ✅ **Direct DOM manipulation** - Ideal for file/progress UIs
- ✅ **Specified in torrent creator spec** - Consistent with requirements

**Alpine.js Features We'll Use:**
```javascript
x-data="torrentCreator()"    // Component state
x-model="form.path"          // Two-way binding
x-show="showAdvanced"        // Conditional display
@click="browseFolder()"      // Event handling
:disabled="!canCreate"       // Dynamic attributes
x-transition                 // Smooth animations
```

### **Styling Framework: Tailwind CSS** ✅
**Why Tailwind?**
- ✅ **Utility-first** - Rapid UI development
- ✅ **Consistent design** - Built-in design system
- ✅ **Dark theme ready** - Matches qBittorrent aesthetic
- ✅ **Responsive by default** - Mobile-friendly
- ✅ **Small production builds** - Only used classes included
- ✅ **Alpine.js friendly** - Perfect for utility-based components

**Tailwind Additions:**
```javascript
// Custom qBittorrent-inspired color palette
colors: {
  qbit: {
    dark: '#2b2b2b',
    darker: '#1e1e1e', 
    accent: '#3daee9',
    success: '#27ae60',
    warning: '#f39c12',
    error: '#e74c3c'
  }
}
```

### **Component Library: Headless UI** ✅
**Why Headless UI?**
- ✅ **Accessibility built-in** - ARIA compliant
- ✅ **Alpine.js integration** - Native support
- ✅ **Unstyled components** - Full design control
- ✅ **Complex interactions** - Modals, dropdowns, toggles

**Components We'll Use:**
- `Listbox` - Piece size selector, alignment dropdown
- `Dialog` - File browser modal, settings overlay
- `Switch` - Private torrent, start seeding toggles
- `Tabs` - Advanced settings sections
- `Disclosure` - Collapsible tracker tiers

### **Icons: Heroicons** ✅
**Why Heroicons?**
- ✅ **Tailwind ecosystem** - Perfect integration
- ✅ **Alpine.js friendly** - SVG components
- ✅ **Professional appearance** - Consistent stroke width
- ✅ **Comprehensive set** - Covers all our needs

---

## **🎨 Visual Design System**

### **Color Palette (Dark Theme First)**
```css
/* Primary Colors */
--qbit-bg-primary: #2b2b2b;      /* Main background */
--qbit-bg-secondary: #3c3c3c;    /* Cards, modals */
--qbit-bg-tertiary: #4a4a4a;     /* Inputs, buttons */

/* Accent Colors */
--qbit-accent: #3daee9;          /* Primary actions */
--qbit-accent-hover: #2980b9;    /* Hover states */

/* Status Colors */
--qbit-success: #27ae60;         /* Success, completed */
--qbit-warning: #f39c12;         /* Warnings, pending */
--qbit-error: #e74c3c;           /* Errors, failed */

/* Text Colors */
--qbit-text-primary: #ffffff;    /* Primary text */
--qbit-text-secondary: #b0b0b0;  /* Secondary text */
--qbit-text-muted: #808080;      /* Disabled, hints */
```

### **Typography Scale**
```css
/* Headings */
.text-qbit-xl    { font-size: 1.5rem; font-weight: 600; }  /* Card titles */
.text-qbit-lg    { font-size: 1.25rem; font-weight: 500; } /* Section headers */
.text-qbit-base  { font-size: 1rem; font-weight: 400; }    /* Body text */
.text-qbit-sm    { font-size: 0.875rem; }                  /* Labels, hints */
.text-qbit-xs    { font-size: 0.75rem; }                   /* Captions */

/* Font Family */
font-family: 'Inter', system-ui, sans-serif; /* Modern, readable */
```

### **Spacing & Layout**
```css
/* Card Spacing */
.qbit-card-padding: 1.5rem;     /* Internal card padding */
.qbit-card-gap: 1rem;           /* Between cards */
.qbit-section-gap: 2rem;        /* Between major sections */

/* Form Elements */
.qbit-input-height: 2.5rem;     /* Standard input height */
.qbit-button-height: 2.5rem;    /* Button height */
.qbit-field-gap: 0.75rem;       /* Between form fields */
```

### **Component Styles**
```css
/* Cards */
.qbit-card {
  @apply bg-qbit-bg-secondary rounded-lg border border-gray-600 shadow-lg;
  @apply p-6 transition-all duration-200;
}

.qbit-card:hover {
  @apply border-qbit-accent/50 shadow-xl;
}

/* Inputs */
.qbit-input {
  @apply bg-qbit-bg-tertiary border border-gray-500 rounded-md;
  @apply text-qbit-text-primary placeholder-qbit-text-muted;
  @apply focus:border-qbit-accent focus:ring-2 focus:ring-qbit-accent/25;
}

/* Buttons */
.qbit-btn-primary {
  @apply bg-qbit-accent hover:bg-qbit-accent-hover;
  @apply text-white font-medium rounded-md transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
}

.qbit-btn-secondary {
  @apply bg-qbit-bg-tertiary hover:bg-gray-500;
  @apply text-qbit-text-primary border border-gray-500;
}
```

---

## **🧩 Component Architecture**

### **Main Application Structure**
```javascript
// Alpine.js Main Component
function torrentCreator() {
  return {
    // State Management
    form: {
      path: '',
      totalBytes: null,
      fileCount: null,
      pieceSizeMode: 'auto',
      pieceSizeBytes: null,
      targetPieces: 2500,
      privateTorrent: true,
      startSeeding: false,
      optimizeAlignment: false,
      announceTiers: [['']],
      webSeeds: [],
      comment: '',
      source: '',
    },
    
    // UI State
    ui: {
      showAdvanced: false,
      isCalculating: false,
      isCreating: false,
      showFileBrowser: false,
      currentTab: 'basic'
    },
    
    // Computed Properties
    get canCalculate() { 
      return this.form.path && this.form.totalBytes > 0; 
    },
    
    get canCreate() { 
      return this.canCalculate && this.form.announceTiers.flat().length > 0; 
    },
    
    // Methods
    async scanPath() { /* API call */ },
    async calculatePieces() { /* API call */ },
    async createTorrent() { /* API call */ },
    
    // File Browser
    async browseFolder() { /* Open modal */ },
    
    // Validation
    validateForm() { /* Validation logic */ }
  }
}
```

### **Component Breakdown**
```html
<!-- Main Container -->
<div x-data="torrentCreator()" class="qbit-app">
  
  <!-- Header -->
  <header class="qbit-header">
    <h1>🔧 Torrent Creator</h1>
    <div class="qbit-status-bar"><!-- Connection status --></div>
  </header>
  
  <!-- Main Content -->
  <main class="qbit-main">
    
    <!-- Card 1: Path Selection -->
    <div class="qbit-card qbit-path-selector">
      <!-- Path input + browse buttons -->
    </div>
    
    <!-- Card 2: Settings -->
    <div class="qbit-card qbit-settings">
      <!-- Piece size, privacy, alignment -->
    </div>
    
    <!-- Card 3: Trackers (Enhanced) -->
    <div class="qbit-card qbit-trackers">
      <!-- Multi-tier tracker editor -->
    </div>
    
    <!-- Card 4: Advanced (Collapsible) -->
    <div x-show="ui.showAdvanced" class="qbit-card qbit-advanced">
      <!-- Web seeds, comments, source -->
    </div>
    
  </main>
  
  <!-- Footer: Progress + Actions -->
  <footer class="qbit-footer">
    <!-- Progress bar + Create/Cancel buttons -->
  </footer>
  
  <!-- Modals -->
  <div x-show="ui.showFileBrowser">
    <!-- File browser modal -->
  </div>
  
</div>
```

---

## **📱 Responsive Design Strategy**

### **Breakpoints**
```css
/* Mobile First Approach */
.qbit-mobile    { /* up to 640px */ }
.qbit-tablet    { /* 641px - 1024px */ }
.qbit-desktop   { /* 1025px+ */ }
```

### **Mobile Layout**
- **Stack cards vertically**
- **Larger touch targets** (44px minimum)
- **Collapsible sections** by default
- **Bottom sheet modals** instead of center modals
- **Thumb-friendly navigation**

### **Tablet Layout**
- **2-column grid** for settings
- **Side-by-side** path + settings
- **Larger preview areas**

### **Desktop Layout**
- **Multi-column layout** like desktop qBittorrent
- **Sidebar navigation** for advanced features
- **Keyboard shortcuts** support
- **Drag-and-drop** enhancements

---

## **⚡ Performance Optimizations**

### **Loading Strategy**
```javascript
// Progressive Loading
1. Load core Alpine.js + Tailwind CSS
2. Load Headless UI components on-demand
3. Lazy load file browser modal
4. Preload common icons
```

### **Bundle Size Targets**
- **Initial Load**: < 100KB (gzipped)
- **Alpine.js**: ~15KB
- **Tailwind CSS**: ~20KB (purged)
- **Headless UI**: ~30KB (selective imports)
- **Custom Code**: ~25KB

### **Caching Strategy**
```javascript
// Service Worker for:
- Static assets (CSS, JS, icons)
- API response caching (path scans)
- Offline functionality (form state)
```

---

## **🎭 Animation & Interactions**

### **Transition Library: Alpine.js Transitions** ✅
```javascript
// Smooth state changes
x-transition:enter="transition duration-300 ease-out"
x-transition:enter-start="opacity-0 transform scale-95"
x-transition:enter-end="opacity-100 transform scale-100"
```

### **Key Animations**
- **Card hover effects** - Subtle elevation + border glow
- **Form validation** - Smooth error state transitions  
- **Progress bars** - Fluid progress updates
- **Modal entrances** - Slide-in from bottom (mobile) / fade-in (desktop)
- **Button interactions** - Micro-interactions on click
- **File browser** - Tree expand/collapse animations

### **Loading States**
```javascript
// Beautiful loading indicators
- Skeleton screens for path scanning
- Pulsing dots for piece calculation
- Progress rings for torrent creation
- Shimmer effects for file lists
```

---

## **♿ Accessibility Features**

### **Keyboard Navigation**
- **Tab order** follows logical flow
- **Arrow keys** for tree navigation
- **Enter/Space** for button activation
- **Escape** for modal dismissal

### **Screen Reader Support**
```html
<!-- ARIA labels -->
<button aria-label="Browse for folder" aria-describedby="path-help">
<div role="progressbar" aria-valuenow="45" aria-valuemax="100">
<fieldset aria-labelledby="tracker-legend">
```

### **Visual Accessibility**
- **High contrast** mode support
- **Focus indicators** always visible
- **Error states** with icons + text
- **Color-blind friendly** status indicators

---

## **🔧 Development Tools**

### **Build Process**
```javascript
// Vite.js for development
- Hot module replacement
- Alpine.js integration
- Tailwind CSS processing
- Production optimization
```

### **Code Quality**
```javascript
// ESLint + Prettier
- Alpine.js specific rules
- Tailwind CSS class ordering
- Accessibility linting
```

### **Testing Strategy**
```javascript
// Cypress for E2E
- Form validation flows
- File browser interactions
- Torrent creation process
- Responsive behavior
```

---

## **📦 Package Dependencies**

```json
{
  "dependencies": {
    "alpinejs": "^3.13.0",
    "@alpinejs/focus": "^3.13.0",
    "@headlessui/alpine": "^1.0.0",
    "@heroicons/heroicons": "^2.0.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.3.0",
    "@tailwindcss/forms": "^0.5.0",
    "@tailwindcss/typography": "^0.5.0",
    "vite": "^4.4.0",
    "cypress": "^13.0.0"
  }
}
```

---

## **🎯 Enhanced Features Beyond Desktop**

### **Smart Defaults**
- **Auto-detect content type** (movie, music, books)
- **Intelligent piece size** suggestions
- **Tracker validation** with real-time feedback
- **Cross-seeding optimization** hints

### **Visual Enhancements**
- **File type icons** in browser
- **Progress visualization** with phases
- **Efficiency scoring** with color coding
- **Tracker tier visualization** with drag-and-drop

### **User Experience**
- **Undo/Redo** for form changes
- **Form auto-save** to localStorage
- **Keyboard shortcuts** (Ctrl+Enter to create)
- **Bulk operations** (multiple trackers)

### **Professional Features**
- **Tracker presets** dropdown
- **Template comments** with variables
- **Export/Import** settings
- **Batch torrent creation**

---

## **🚀 Implementation Timeline**

### **Phase 1: Core Structure (2-3 days)**
- ✅ Alpine.js + Tailwind setup
- ✅ Basic card layout matching desktop
- ✅ Path selection with file browser
- ✅ Settings panel (piece size, privacy)

### **Phase 2: Advanced Features (2-3 days)**  
- ✅ Multi-tier tracker editor
- ✅ Piece size calculator integration
- ✅ Form validation with real-time feedback
- ✅ Progress visualization

### **Phase 3: Polish & Enhancement (1-2 days)**
- ✅ Animations and micro-interactions
- ✅ Mobile responsive design
- ✅ Accessibility improvements  
- ✅ Performance optimizations

### **Phase 4: Advanced Features (1-2 days)**
- ✅ Tracker presets system
- ✅ Template comments
- ✅ Export/import functionality
- ✅ Advanced settings panel

---

## **🎨 Design Inspiration**

### **Desktop qBittorrent**: Functional layout and workflow
### **Modern Web Apps**: 
- **Discord** - Card-based layout, dark theme
- **Figma** - Clean interface, progressive enhancement
- **Linear** - Smooth animations, keyboard shortcuts
- **Vercel** - Minimalist design, excellent UX

### **Color Psychology**
- **Dark theme** reduces eye strain during long sessions
- **Blue accents** convey trust and professionalism  
- **Green success states** provide positive feedback
- **Subtle animations** make the interface feel responsive

---

**This technology stack will create a torrent creator that's not just functional, but delightful to use! 🎯**
