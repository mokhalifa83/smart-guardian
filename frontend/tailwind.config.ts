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
          950: "#04070d",
          900: "#070c16",
          850: "#0b1322",
          800: "#0f1a2e",
          750: "#14223d",
          700: "#192c4e",
          600: "#243c68",
          500: "#36558c",
          accent: "#00e5ff",
          cyanGlow: "#00f0ff",
          emeraldGlow: "#10b981",
          warning: "#f59e0b",
          critical: "#f43f5e",
          success: "#10b981",
          unavailable: "#64748b",
        },
      },
      fontFamily: {
        cairo: ["var(--font-cairo)", "Cairo", "system-ui", "-apple-system", "sans-serif"],
        sans: ["var(--font-cairo)", "Cairo", "system-ui", "-apple-system", "sans-serif"],
        arabic: ["var(--font-cairo)", "Cairo", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 20px -5px rgba(0, 229, 255, 0.25)",
        "glow-emerald": "0 0 20px -5px rgba(16, 185, 129, 0.25)",
        "glow-amber": "0 0 20px -5px rgba(245, 158, 11, 0.25)",
        "glow-rose": "0 0 20px -5px rgba(244, 63, 94, 0.25)",
      },
    },
  },
  plugins: [],
};
export default config;
