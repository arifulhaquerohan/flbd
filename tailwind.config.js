module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#111113",
          black: "#0b0b0f",
          gold: "#ff5a3d",
          "gold-light": "#ffe4dd",
          "gold-dark": "#d9482f",
          warm: "#fff4ee",
          soft: "#f6f4ef",
          ink: "#111113",
          muted: "#6b6b73"
        },
        glass: {
          bg: "rgba(255, 255, 255, 0.75)",
          border: "rgba(17, 17, 19, 0.12)",
          "border-subtle": "rgba(17, 17, 19, 0.08)"
        }
      },
      fontFamily: {
        sans: ["Space Grotesk", "sans-serif"],
        display: ["Fraunces", "serif"]
      },
      borderRadius: {
        xl: "24px",
        "2xl": "32px",
        "3xl": "40px"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(16, 17, 21, 0.08)",
        strong: "0 24px 60px rgba(16, 17, 21, 0.16)",
        glow: "0 0 24px rgba(255, 90, 61, 0.25)"
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        "slow-zoom": {
          "0%": { transform: "scale(1)" },
          "100%": { transform: "scale(1.1)" }
        }
      },
      animation: {
        "fade-in-up": "fade-in-up 0.8s ease-out forwards",
        "slow-zoom": "slow-zoom 20s linear infinite alternate"
      }
    }
  }
};
