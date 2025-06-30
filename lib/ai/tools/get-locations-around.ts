import { tool } from "ai";
import { z } from "zod";

const api_key = process.env["2GIS_API_KEY"];

export const getLocationsAround = tool({
  description:
    "Get a list of locations around the given coordinates, optionally filtered by a search query (e.g., 'кафе'). Supports radius, page size, and sorting by distance. Returns name, type, and address for each location.",
  parameters: z
    .object({
      description: z
        .string()
        .describe(
          "Short description to show to the user when calling the tool.",
        ),
      longitude: z.number().describe("The longitude of the center point."),
      latitude: z.number().describe("The latitude of the center point."),
      query: z
        .string()
        .optional()
        .describe("Optional search query, e.g., 'кафе'."),
      page_size: z
        .number()
        .int()
        .min(1)
        .max(50)
        .optional()
        .describe("Number of results per page (max 10 for demo key)."),
      page: z
        .number()
        .int()
        .min(1)
        .optional()
        .describe("Page number (max 5 for demo key)."),
      radius: z
        .number()
        .int()
        .min(1)
        .optional()
        .describe("Search radius in meters."),
      sort: z
        .enum(["distance"])
        .optional()
        .describe("Sort by 'distance' if provided."),
    })
    .describe("Parameters for getting locations around a point."),
  execute: async ({
    longitude,
    latitude,
    query,
    page_size,
    page,
    radius,
    sort,
  }) => {
    try {
      if (!api_key) {
        throw new Error("2GIS_API_KEY is not set in environment variables.");
      }
      const baseUrl = "https://catalog.api.2gis.com/3.0/items";
      const params = [
        query ? `q=${encodeURIComponent(query)}` : null,
        `fields=items.point,items.name,items.type,items.address_name,items.full_name,items.purpose_name`,
        `key=${api_key}`,
        page_size ? `page_size=${page_size}` : null,
        page ? `page=${page}` : null,
        radius ? `radius=${radius}` : null,
        sort ? `sort=${sort}` : null,
        // Use both point and location for best results if radius or sort is set
        radius || sort
          ? `point=${longitude},${latitude}`
          : `location=${longitude},${latitude}`,
      ]
        .filter(Boolean)
        .join("&");
      const url = `${baseUrl}?${params}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(
          `2GIS API error: ${response.status} ${response.statusText}`,
        );
      }
      const data = await response.json();
      const items = data?.result?.items ?? [];
      return items.map((item: any) => ({
        name: item.name ?? null,
        type: item.type ?? null,
        address_name: item.address_name ?? null,
        full_name: item.full_name ?? null,
        purpose_name: item.purpose_name ?? null,
        point: item.point ?? null,
      }));
    } catch (error) {
      console.error("Error fetching locations:", error);
      return { error };
    }
  },
});
