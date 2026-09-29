/** Pre-built Tailwind (replaces the in-browser Play CDN, which is slow on phones).
 *  Rebuild: npx tailwindcss@3 -c tailwind.config.js -i tailwind.input.css -o static/tw.css --minify
 *  (the deploy workflows rebuild it automatically) */
module.exports = {
  darkMode: 'class',
  content: ['./static/index.html', './static/app.js', './static/i18n.js'],
  theme: { extend: {} },
  plugins: [],
};
