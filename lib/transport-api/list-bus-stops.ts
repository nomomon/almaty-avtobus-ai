import { getApiHeaders } from ".";

// Bus stop name in multiple languages
export interface BusStopName {
  ru: string;
  kz: string;
  en: string;
}

// Bus stop object returned by the API
export interface RawBusStop {
  id: number;
  name: BusStopName;
  point: [number, number]; // [latitude, longitude]
  routes: number[];
  updatedAt: string;
}
export interface BusStop extends Omit<RawBusStop, "point"> {
  location: {
    latitude: number;
    longitude: number;
  };
}

export async function listBusStops(): Promise<BusStop[]> {
  const response = await fetch("https://cdu-rest-api.tha.kz/stop/list", {
    method: "GET",
    headers: getApiHeaders({
      accept: "application/json, text/plain, */*",
    }),
  });

  if (!response.ok) {
    console.error(
      `[THA-API] Failed to fetch bus stops: ${response.statusText}`,
    );
    throw new Error(`Failed to fetch bus stops: ${response.status}`);
  }

  const rawStops: RawBusStop[] = await response.json();

  const stops: BusStop[] = rawStops.map((stop) => ({
    ...stop,
    location: {
      latitude: stop.point[0],
      longitude: stop.point[1],
    },
  }));
  console.log(`[THA-API] Fetched ${stops.length} bus stops`);

  return stops;
}

export function computeDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  // Approximate distance in meters using Pythagorean theorem (for small distances)
  const dLat = lat1 - lat2;
  const dLon = lon1 - lon2;
  return Math.sqrt(Math.pow(dLat, 2) + Math.pow(dLon, 2)) * 111320;
}

export async function getClosestBusStops(
  latitude: number,
  longitude: number,
  radius: number = 500,
): Promise<BusStop[]> {
  const stops = await listBusStops();
  // Calculate distance for each stop and filter by radius
  const stopsWithDistance = stops.map((stop) => {
    const distance = computeDistance(
      stop.location.latitude,
      stop.location.longitude,
      latitude,
      longitude,
    );
    return {
      stop,
      distance,
    };
  });
  // Filter by radius and sort by distance
  const goodStops = stopsWithDistance
    .filter(({ distance }) => distance <= radius)
    .sort((a, b) => a.distance - b.distance)
    .map(({ stop }) => stop);

  console.log(
    `[THA-API] Found ${goodStops.length} bus stops within ${radius}m radius`,
  );

  return goodStops;
}
