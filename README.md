# Almaty Avtobus AI

![Almaty Avtobus AI](assets/icon.svg)

**Chat with an AI that knows Almaty’s buses.** Ask for nearby stops, when the next bus is coming, or how to get from A to B. It uses the city transport API and talks back in Russian, English, or Kazakh.

## What it does

- **Nearby stops** — Finds bus stops near you and walking times.
- **Live departures** — Shows which buses are coming and when.
- **Route planning** — Suggests how to get between two points by bus.
- **Places** — Describes points of interest and locations in Almaty.

All of this is driven by a chat interface: you ask in natural language, the assistant calls tools (location, transit API, routes) and answers. Installable as a PWA.

## Tech

- **Next.js 15** (App Router) + **React 19**
- **Vercel AI SDK** with **Google Gemini 2.5 Flash**
- **Almaty transport API** for stops, routes, and arrivals
- **Tailwind CSS**, **Framer Motion**, **Radix** for UI
- **PWA** (manifest, install prompt, service worker)

## How to run

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). You’ll need a `GOOGLE_GENERATIVE_AI_API_KEY` (or equivalent) for the AI SDK; the transport API is wired with its own auth in the repo.

## Build

```bash
pnpm build
pnpm start
```

---

*Side project: an AI assistant for Almaty’s bus network, with real-time data and a simple chat UI.*
