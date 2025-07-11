import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Almaty Avtobus AI",
    short_name: "Bus AI",
    description: "AI-ассистент для поиска автобусов и остановок в Алматы.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#d69300",
    icons: [
      {
        src: "/web-app-manifest-192x192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/web-app-manifest-512x512.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/apple-icon.png",
        sizes: "180x180",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon1.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/icon0.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
