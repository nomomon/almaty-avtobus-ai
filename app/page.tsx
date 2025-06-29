"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit } = useChat();

  return (
    <div>
      <div>
        {messages.map((message) => (
          <div key={message.id} className="mb-4">
            <div className="font-bold">{message.role}</div>
            <div>
              {message.parts.map((part, i) => (
                <p key={i} className="text-gray-800">
                  {part.type === "text" && part.text}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="flex flex-row gap-4">
        <Textarea value={input} onChange={handleInputChange} />
        <Button className="h-8 w-8" onClick={handleSubmit}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
