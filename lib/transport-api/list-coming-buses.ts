import { getApiHeaders } from ".";

export interface ComingBus {
  routeId: number;
  distance: number;
  time: number;
  data: {
    ru: string;
    kk: string;
    en: string;
  };
}

export const listComingBuses = async (stopId: number): Promise<ComingBus[]> => {
  const response = await fetch(
    `https://cdu-rest-api.tha.kz/arrival-board/stop/${stopId}`,
    {
      method: "POST",
      headers: getApiHeaders({
        accept: "application/json, text/plain, */*",
        contentType: "application/json;charset=UTF-8",
      }),
      body: "[]",
    },
  );

  if (!response.ok) {
    console.error(
      `[THA-API] Failed to fetch coming buses for stop ${stopId}: ${response.statusText}`,
    );
    throw new Error(`Failed to fetch coming buses: ${response.status}`);
  }
  const data: ComingBus[] = await response.json();

  console.log(
    `[THA-API] Fetched ${data.length} coming buses for stop ${stopId}`,
  );

  return data;
};
