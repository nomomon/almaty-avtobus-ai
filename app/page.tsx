"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";
import { useEnterSubmit } from "@/lib/hooks/use-enter-submit";
import Chat from "@/components/templates/chat";

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, addToolResult } =
    useChat();
  const { handleKeyDown } = useEnterSubmit();

  return (
    <div className="flex flex-col h-screen p-4 gap-4">
      <Chat messages={messages} addToolResult={addToolResult} />
      <div className="flex flex-row gap-4">
        <Textarea
          autoFocus
          value={input}
          onChange={handleInputChange}
          onKeyDown={(e) => handleKeyDown(e, handleSubmit)}
          placeholder="Введите сообщение..."
        />
        <Button className="h-8 w-8" onClick={handleSubmit}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
