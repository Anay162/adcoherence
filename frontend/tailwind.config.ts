import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Score color scale
        score: {
          red: "#EF4444",
          yellow: "#F59E0B",
          green: "#22C55E",
        },
      },
    },
  },
  plugins: [],
};

export default config;
