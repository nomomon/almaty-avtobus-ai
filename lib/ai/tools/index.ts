import { getLocationsAround } from "./get-locations-around";
import { getPointDescription } from "./get-point-description";
import { getRoute } from "./get-route";
import { getTransitData } from "./get-transit-data";
import { getUserLocation } from "./get-user-location";

const tools = {
  getUserLocation,
  getTransitData,
  getPointDescription,
  getLocationsAround,
  getRoute,
};

export default tools;
