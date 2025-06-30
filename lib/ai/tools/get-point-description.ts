import { tool } from "ai";
import { describe } from "node:test";
import { z } from "zod";

const api_key = process.env["2GIS_API_KEY"];

export const getPointDescription = tool({
  description:
    "Get a description of a point in the city, including its name, type, and any relevant details.",
  parameters: z
    .object({
      description: z
        .string()
        .describe("Description to show to the user when calling the tool."),
      longitude: z.number().describe("The longitude of the point."),
      latitude: z.number().describe("The latitude of the point."),
    })
    .describe("Parameters for getting a point description."),
  execute: async ({ longitude, latitude }) => {
    if (!api_key) {
      throw new Error("2GIS_API_KEY is not set in environment variables.");
    }
    const url = `https://catalog.api.2gis.com/3.0/items/geocode?lon=${longitude}&lat=${latitude}&fields=items.point,items.name,items.type,items.address_name,items.full_name,items.purpose_name&key=${api_key}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `2GIS API error: ${response.status} ${response.statusText}`,
      );
    }
    const data = await response.json();
    const item = data?.result?.items?.[0] || {};
    return {
      name: item.name ?? null,
      type: item.type ?? null,
      address_name: item.address_name ?? null,
      full_name: item.full_name ?? null,
      purpose_name: item.purpose_name ?? null,
    };
  },
});
