export const API_BASE =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? "http://whatif_api:5000")   // chiamate SSR
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5003"); // chiamate dal browser
