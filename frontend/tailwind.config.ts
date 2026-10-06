import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { aghuse: { 50: '#eef4ff', 500: '#2563eb', 700: '#1d4ed8' } },
      boxShadow: { panel: '0 10px 28px rgba(30,55,90,.06)' },
    },
  },
  plugins: [],
} satisfies Config;
