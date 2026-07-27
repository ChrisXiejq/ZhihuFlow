/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        ink: "#07090f",
        panel: "rgba(13, 18, 31, 0.74)",
        cyan: "#55f5ff",
        gold: "#f8d26a",
        danger: "#ff5d7a",
        success: "#72f2a7",
      },
      boxShadow: {
        glow: "0 24px 80px rgba(85, 245, 255, 0.18)",
        panel: "0 28px 90px rgba(0, 0, 0, 0.42)",
      },
      fontFamily: {
        display: ['"Avenir Next"', '"PingFang SC"', '"Hiragino Sans GB"', "sans-serif"],
        mono: ['"SF Mono"', "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
