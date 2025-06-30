import { tool } from "ai";
import { z } from "zod";

const api_key = process.env["2GIS_API_KEY"];

export const getRoute = tool({
  description:
    "Get a public transport route between two points using 2GIS. Returns route details including distance, duration, transfers, and transport types.",
  parameters: z
    .object({
      description: z
        .string()
        .describe(
          "Short description to show to the user when calling the tool.",
        ),
      source: z.object({
        name: z.string().describe("Name of the starting point."),
        latitude: z.number().describe("Latitude of the starting point."),
        longitude: z.number().describe("Longitude of the starting point."),
      }),
      target: z.object({
        name: z.string().describe("Name of the destination point."),
        latitude: z.number().describe("Latitude of the destination point."),
        longitude: z.number().describe("Longitude of the destination point."),
      }),
      transport: z
        .array(
          z
            .enum(["bus", "tram", "trolleybus", "minibus", "metro"])
            .describe("Transport type"),
        )
        .optional(),
      locale: z.string().optional().describe("Locale, e.g., 'ru' or 'en'."),
    })
    .describe("Parameters for getting a public transport route."),
  execute: async ({ source, target, transport, locale }) => {
    if (!api_key) {
      throw new Error("2GIS_API_KEY is not set in environment variables.");
    }
    const url = `https://routing.api.2gis.com/public_transport/2.0?key=${api_key}`;
    const body = {
      locale: locale ?? "ru",
      source: {
        name: source.name,
        point: { lat: source.latitude, lon: source.longitude },
      },
      target: {
        name: target.name,
        point: { lat: target.latitude, lon: target.longitude },
      },
      ...(transport ? { transport } : {}),
    };
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(
        `2GIS API error: ${response.status} ${response.statusText}`,
      );
    }
    const data = await response.json();

    return data.map((route: Record<string, unknown>) => {
      if ("movements" in route) {
        delete route.movements;
      }
      return route;
    });
  },
});
