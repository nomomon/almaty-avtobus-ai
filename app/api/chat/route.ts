import { google } from "@ai-sdk/google";
import { streamText, Message } from "ai";

export async function POST(req: Request) {
  const { messages }: { messages: Message[] } = await req.json();

  const result = streamText({
    model: google("gemini-1.5-flash"),
    messages,
  });

  return result.toDataStreamResponse();
}
