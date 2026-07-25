/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./**/*.html", "../**/*.{ex,exs}"],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
