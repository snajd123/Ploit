/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        poker: {
          green: '#0F5132',
          felt: '#1B5E20',
          chip: '#FFD700',
        }
      }
    },
  },
  plugins: [],
}
