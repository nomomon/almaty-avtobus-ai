import { tool } from "ai";
import z from "zod";

export const getUserLocation = tool({
  description: "Get the user's current location",
  parameters: z.object({}),
  execute: async () => {
    const location = {
      latitude: 37.7749, // Example latitude
      longitude: -122.4194, // Example longitude
      city: "San Francisco", // Example city
      country: "USA", // Example country
    };

    return { location };
  },
});
