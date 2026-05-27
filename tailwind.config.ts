import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        display: ["var(--font-display)", "var(--font-sans)", "system-ui"],
      },
      colors: {
        neon: {
          cyan: "#22d3ee",
          violet: "#a78bfa",
          fuchsia: "#e879f9",
        },
      },
      boxShadow: {
        glow: "0 0 32px -8px rgba(34, 211, 238, 0.35)",
        panel: "inset 0 1px 0 0 rgba(255,255,255,0.06), 0 24px 48px -24px rgba(0,0,0,0.8)",
      },
    },
  },
  plugins: [],
} satisfies Config;
