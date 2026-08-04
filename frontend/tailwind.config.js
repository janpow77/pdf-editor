/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  // Klassensteuerung ist erforderlich, damit der manuelle Schalter die
  // Systempräferenz überstimmen kann. `useTheme` setzt die Klasse zentral.
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Apple-nahe Systemschrift ohne externen Font-Download: auf macOS wird
        // San Francisco verwendet, auf anderen Plattformen die native UI-Schrift.
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Text', 'Segoe UI', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        apple: '1rem',
        'apple-lg': '1.35rem',
      },
      boxShadow: {
        // Mehrere dezente Ebenen wirken weicher als ein harter Standard-Schatten.
        'apple-sm': '0 8px 24px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.05)',
        apple: '0 18px 45px rgba(15,23,42,.08), 0 2px 8px rgba(15,23,42,.05)',
        'apple-hover': '0 24px 60px rgba(15,23,42,.13), 0 4px 12px rgba(15,23,42,.08)',
      },
      colors: {
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
