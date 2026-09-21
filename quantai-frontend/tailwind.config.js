/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Background
        bg: {
          primary: '#0f172a',
          secondary: '#1e293b',
          tertiary: '#334155',
          elevated: '#1e293b',
        },
        // Surface
        surface: {
          DEFAULT: '#1e293b',
          hover: '#334155',
          active: '#475569',
        },
        // Border
        border: {
          subtle: '#334155',
          DEFAULT: '#475569',
          strong: '#64748b',
        },
        // Accent - Professional
        accent: {
          primary: '#3b82f6',
          secondary: '#6366f1',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          info: '#0ea5e9',
        },
        // Text
        text: {
          primary: '#f8fafc',
          secondary: '#cbd5e1',
          tertiary: '#94a3b8',
          muted: '#64748b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
