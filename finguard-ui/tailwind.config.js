/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0d1117',
        surface: '#161b22',
        border: '#21262d',
        primary: '#e6edf3',
        secondary: '#8b949e',
        muted: '#484f58',
        decision: {
          approve: '#3fb950',
          warn: '#d29922',
          delay: '#f0883e',
          block: '#f85149'
        },
        user: {
          aman: '#58a6ff',
          riya: '#bc8cff',
          kabir: '#ffa657'
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
