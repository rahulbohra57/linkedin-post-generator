import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        linkedin: {
          blue: "#0A66C2",
          "blue-dark": "#004182",
          "blue-light": "#EAF4FE",
        },
      },
    },
  },
  plugins: [],
};

export default config;
