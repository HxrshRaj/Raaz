import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#090d14", 900: "#0b0f17", 800: "#10151f", 700: "#161d2a", 600: "#1d2636", 500: "#2a3547" },
        paper: { DEFAULT: "#e9e2d0", dim: "#c9c2b0", mute: "#8e98a8" },
        amber: { glow: "#f2a94e", deep: "#c9822a" },
        brass: { DEFAULT: "#b8924f", light: "#d9b572", dark: "#7d6130" },
        blood: { DEFAULT: "#c2412d", light: "#e0634e" },
        rain: "#6f87a6",
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', '"Playfair Display"', "Georgia", "serif"],
        body: ['"Inter"', "system-ui", "sans-serif"],
        type: ['"Special Elite"', '"Courier New"', "monospace"],
        deva: ['"Tiro Devanagari Hindi"', '"Noto Serif Devanagari"', "serif"],
      },
      boxShadow: {
        lamp: "0 0 40px 6px rgba(242,169,78,0.25)",
        card: "0 8px 30px rgba(0,0,0,0.45)",
      },
      keyframes: {
        flicker: { "0%,100%": { opacity: "1" }, "47%": { opacity: "0.92" }, "50%": { opacity: "0.75" }, "53%": { opacity: "0.95" } },
        pulseRing: { "0%": { transform: "scale(0.8)", opacity: "0.8" }, "100%": { transform: "scale(1.9)", opacity: "0" } },
        rise: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: {
        flicker: "flicker 5s infinite",
        pulseRing: "pulseRing 2.2s ease-out infinite",
        rise: "rise .35s ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;
