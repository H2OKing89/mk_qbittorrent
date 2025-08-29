/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './static/src/**/*.{html,js}',
    './templates/**/*.html',
    '../templates/**/*.html'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        qbit: {
          // Dark theme colors matching qBittorrent desktop
          dark: '#2b2b2b',
          darker: '#1e1e1e',
          darkest: '#1a1a1a',
          accent: '#3daee9',
          'accent-hover': '#2980b9',
          'accent-light': '#85c1e9',
          success: '#27ae60',
        },
        // Named colors for the new professional UI
        'qbit-bg-primary': '#2b2b2b',
        'qbit-bg-secondary': '#3c3c3c',
        'qbit-bg-tertiary': '#4a4a4a',
        'qbit-accent': '#3daee9',
        'qbit-accent-hover': '#2980b9',
        'qbit-success': '#27ae60',
        'qbit-warning': '#f39c12',
        'qbit-error': '#e74c3c',
        'qbit-text-primary': '#ffffff',
        'qbit-text-secondary': '#b0b0b0',
        'qbit-text-muted': '#808080',
          'success-light': '#58d68d',
          warning: '#f39c12',
          'warning-light': '#f8c471',
          error: '#e74c3c',
          'error-light': '#ec7063',
          
          // Background colors
          'bg-primary': '#2b2b2b',
          'bg-secondary': '#3c3c3c',
          'bg-tertiary': '#4a4a4a',
          'bg-quaternary': '#5a5a5a',
          'bg-hover': '#404040',
          
          // Text colors
          'text-primary': '#ffffff',
          'text-secondary': '#e0e0e0',
          'text-muted': '#b0b0b0',
          'text-disabled': '#808080',
          
          // Border colors
          'border-primary': '#555555',
          'border-secondary': '#666666',
          'border-accent': '#3daee9',
          
          // Input colors
          'input-bg': '#3c3c3c',
          'input-border': '#555555',
          'input-focus': '#3daee9'
        }
      },
      fontFamily: {
        'inter': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Monaco', 'Consolas', 'monospace']
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }]
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem'
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' }
        }
      },
      boxShadow: {
        'qbit': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'qbit-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2)',
        'qbit-inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)'
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/container-queries')
  ]
}
