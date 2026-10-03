/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#111111",
        mute: "#6b7280",
        line: "#ececec",
        accent: "#3b82f6",
      },
      boxShadow: {
        input: "0 10px 40px -18px rgba(59, 130, 246, 0.35)",
      },
    },
  },
  plugins: [],
};
