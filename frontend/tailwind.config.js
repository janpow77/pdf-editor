/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        // Eine systemweite Akzentfarbe (Apple-nahes Blau)
        primary: {
          50: '#f0f7ff',
          100: '#dcecfd',
          400: '#4b9bf5',
          500: '#1e85ec',
          600: '#0071e3',
          700: '#0066cc',
          900: '#0a3f75',
        },
      },
    },
  },
  plugins: [],
}
