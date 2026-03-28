import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        up: "#ef4444",
        down: "#3b82f6",
        bg: {
          primary: "#0a0a0a",
          secondary: "#141414",
          card: "#1a1a1a",
          hover: "#242424",
        },
        border: {
          DEFAULT: "#2d2d2d",
        },
      },
    },
  },
  plugins: [],
};

export default config;
