"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";
import { useEnterSubmit } from "@/lib/hooks/use-enter-submit";
import { ToolCall } from "@/components/tools";

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, addToolResult } =
    useChat();
  const { handleKeyDown } = useEnterSubmit();

  return (
    <div>
      <div>
        {messages.map((message) => (
          <div key={message.id} className="mb-4">
            <div className="font-bold">{message.role}</div>
            <div>
              {message.parts.map((part, i) => (
                <div key={`${message.id}-${i}`} className="text-gray-800">
                  {part.type === "text" && <p>{part.text}</p>}
                  {part.type === "tool-invocation" && (
                    <ToolCall
                      toolInvocation={part.toolInvocation}
                      addToolResult={addToolResult}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="flex flex-row gap-4">
        <Textarea
          value={input}
          onChange={handleInputChange}
          onKeyDown={(e) => handleKeyDown(e, handleSubmit)}
          placeholder="Type your message here..."
        />
        <Button className="h-8 w-8" onClick={handleSubmit}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
