import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50:"#eef7ff",100:"#d9ecff",200:"#b3d9ff",300:"#85c2ff",
                 400:"#56a7ff",500:"#2e89ff",600:"#196ee6",700:"#1559b4",
                 800:"#124a91",900:"#103f79" }
      },
      boxShadow: { card: "0 2px 8px rgba(0,0,0,0.06), 0 10px 20px rgba(0,0,0,0.04)" }
    }
  },
  plugins: []
} satisfies Config;
