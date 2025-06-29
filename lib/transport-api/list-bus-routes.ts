import { getApiHeaders } from ".";

// Route name in multiple languages
export interface RouteName {
  ru: string;
  kk: string;
  en: string;
}

// Stop along a route direction
export interface RouteStop {
  stopId: number;
  lineIndex: number;
  offsetDistance: number;
  distance: number;
  longitude: number;
  latitude: number;
}

// Direction of a route
export interface RouteDirection {
  index: number;
  line: [number, number][]; // [latitude, longitude][]
  distance: number;
  stops: RouteStop[];
}

// Raw route object returned by the API
export interface RawBusRoute {
  id: number;
  typeId: number;
  name: RouteName;
  directions: RouteDirection[];
  updatedAt: string;
}

// Usable bus route object
export interface BusRoute extends Omit<RawBusRoute, "directions"> {
  directions: RouteDirection[];
}

export async function listBusRoutes(): Promise<BusRoute[]> {
  const response = await fetch("https://cdu-rest-api.tha.kz/route/list", {
    method: "GET",
    headers: getApiHeaders({
      accept: "application/json, text/plain, */*",
    }),
  });

  if (!response.ok) {
    console.error(
      `[THA-API] Failed to fetch bus routes: ${response.statusText}`,
    );
    throw new Error(`Failed to fetch bus routes: ${response.status}`);
  }

  const rawRoutes: RawBusRoute[] = await response.json();

  // No transformation needed, but you can add mapping here if needed
  const routes: BusRoute[] = rawRoutes.map((route) => ({
    ...route,
    // directions are already in the correct format
  }));
  console.log(`[THA-API] Fetched ${routes.length} bus routes`);

  return routes;
}
