import { tool } from "ai";
import z from "zod";

export const getUserLocation = tool({
  description:
    "Get the user's current location, call without asking for permission",
  parameters: z.object({
    description: z
      .string()
      .describe("Description to show to the user when calling the tool."),
  }),
});
