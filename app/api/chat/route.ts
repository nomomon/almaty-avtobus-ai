import tools from "@/lib/ai/tools";
import { google } from "@ai-sdk/google";
import { streamText, Message } from "ai";

export async function POST(req: Request) {
  const { messages }: { messages: Message[] } = await req.json();

  const result = streamText({
    model: google("gemini-1.5-flash"),
    system:
      "You are a helpful assistant that can answer questions and provide information.",
    messages,
    tools,
    maxSteps: 2,
  });

  return result.toDataStreamResponse();
}
