import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        oilfield: {
          950: "#000000",
          900: "#0a0a0a",
          850: "#111111",
          800: "#161618",
          750: "#1c1c1f",
          700: "#26262a",
          600: "#3f3f46",
          500: "#52525b",
          accent: "#ef4444",
          cyanGlow: "#f87171",
          emeraldGlow: "#22c55e",
          warning: "#ef4444",
          critical: "#dc2626",
          success: "#22c55e",
          unavailable: "#71717a",
        },
        brand: {
          red: "#ef4444",
          redDark: "#dc2626",
          redDeep: "#991b1b",
          redGlow: "rgba(239, 68, 68, 0.4)",
        },
      },
      fontFamily: {
        cairo: ["var(--font-cairo)", "Cairo", "system-ui", "-apple-system", "sans-serif"],
        sans: ["var(--font-cairo)", "Cairo", "system-ui", "-apple-system", "sans-serif"],
        arabic: ["var(--font-cairo)", "Cairo", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 25px -4px rgba(239, 68, 68, 0.35)",
        "glow-red": "0 0 30px -4px rgba(220, 38, 38, 0.45)",
        "glow-emerald": "0 0 20px -5px rgba(34, 197, 94, 0.25)",
        "glow-amber": "0 0 20px -5px rgba(239, 68, 68, 0.35)",
        "glow-rose": "0 0 20px -5px rgba(220, 38, 38, 0.4)",
      },
    },
  },
  plugins: [],
};
export default config;
