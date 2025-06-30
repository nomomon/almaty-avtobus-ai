import tools from "@/lib/ai/tools";
import { google } from "@ai-sdk/google";
import { streamText, Message, smoothStream } from "ai";

export async function POST(req: Request) {
  const { messages }: { messages: Message[] } = await req.json();

  const result = streamText({
    model: google("gemini-2.5-flash"),
    system:
      "Ты – опытный помощник с доступом к информации о маршрутах общественного транспорта в Алматы. Твоя задача – помочь пользователю найти оптимальный маршрут на автобусе, учитывая его начальную и конечную точки. У тебя есть доступ к геолокации пользователя и информации о маршрутах автобусов. Используй эту информацию, чтобы предложить наиболее подходящий маршрут.",
    messages,
    tools,
    maxSteps: 10,
    toolCallStreaming: true,
    experimental_transform: smoothStream({ chunking: "word" }),
  });

  return result.toDataStreamResponse();
}
