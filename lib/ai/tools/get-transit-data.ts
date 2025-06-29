import { listBusRoutes } from "@/lib/transport-api/list-bus-routes";
import {
  computeDistance,
  getClosestBusStops,
} from "@/lib/transport-api/list-bus-stops";
import { listComingBuses } from "@/lib/transport-api/list-coming-buses";
import { tool } from "ai";
import z from "zod";

export const getTransitData = tool({
  description: "",
  parameters: z.object({
    location: z
      .object({
        latitude: z.number(),
        longitude: z.number(),
      })
      .describe("User's location"),
    radius: z
      .number()
      .optional()
      .describe("Search radius in meters")
      .default(400),
  }),
  execute: async ({ location, radius = 400 }) => {
    console.log(
      "Fetching bus stops within radius:",
      radius,
      "meters from location:",
      location,
    );
    const routes = await listBusRoutes();

    const busStops = (
      await getClosestBusStops(location.latitude, location.longitude, radius)
    ).slice(0, 2);

    console.log(JSON.stringify(busStops, null, 2));

    const nearbyStops = [];

    for (const stop of busStops) {
      const distance = computeDistance(
        location.latitude,
        location.longitude,
        stop.location.latitude,
        stop.location.longitude,
      );
      // Average walking speed ~80 m/min
      const walkingTime = Math.round(distance / 80);
      const comingBuses = await listComingBuses(stop.id);

      nearbyStops.push({
        stopId: stop.id.toString(),
        name: stop.name.en,
        distance: Math.round(distance),
        walkingTime,
        departures: comingBuses.map((bus) => ({
          ...bus,
          routeName: routes.find((route) => route.id === bus.routeId)?.name.en,
        })),
      });
    }

    return { nearbyStops };
  },
});
