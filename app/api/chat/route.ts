import { google } from "@ai-sdk/google";
import { streamText, Message, smoothStream } from "ai";
import tools from "@/lib/ai/tools";
import { systemPrompt } from "@/lib/ai/prompts";

export async function POST(req: Request) {
  const { messages }: { messages: Message[] } = await req.json();

  const result = streamText({
    model: google("gemini-2.5-flash"),
    system: systemPrompt,
    messages,
    tools,
    maxSteps: 10,
    toolCallStreaming: true,
    experimental_transform: smoothStream({ chunking: "word" }),
  });

  return result.toDataStreamResponse();
}
