/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        // Divimero palette (light-first)
        bg: "#FFFFFF",
        surface: "#F1F5F7",
        line: "#E3E3E3",
        ink: "#171717",
        mute: "#72777F",
        brand: {
          DEFAULT: "#35C7B2",
          soft: "#E1F4F1",
        },
        violet: {
          DEFAULT: "#7361F7",
          soft: "#E6E2FD",
        },
        pos: "#12BD57",
        neg: "#FF3B30",
        warn: "#D6B130",
        warnSoft: "#FFF8DF",
        orange: "#FF7733",
        orangeSoft: "#FFE4D6",

        // shadcn tokens mapped to the light theme
        background: "#FFFFFF",
        foreground: "#171717",
        card: { DEFAULT: "#FFFFFF", foreground: "#171717" },
        popover: { DEFAULT: "#FFFFFF", foreground: "#171717" },
        primary: { DEFAULT: "#35C7B2", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#F1F5F7", foreground: "#171717" },
        muted: { DEFAULT: "#F1F5F7", foreground: "#72777F" },
        accent: { DEFAULT: "#E6E2FD", foreground: "#7361F7" },
        destructive: { DEFAULT: "#FF3B30", foreground: "#FFFFFF" },
        border: "#E3E3E3",
        input: "#E3E3E3",
        ring: "#35C7B2",
      },
      fontFamily: {
        heading: ['Outfit', 'ui-sans-serif', 'system-ui'],
        body: ['Manrope', 'ui-sans-serif', 'system-ui'],
        sans: ['Manrope', 'ui-sans-serif', 'system-ui'],
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.15rem",
      },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
        'fade-up': { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-up': 'fade-up 0.3s ease-out both',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
