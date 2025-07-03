"use client";

import { useChat } from "@ai-sdk/react";
import Chat from "@/components/templates/chat";
import Logo from "@/components/atoms/logo";
import InstallPrompt from "@/components/atoms/install-prompt";
import ChatInput from "@/components/molecules/chat-input";

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, addToolResult } =
    useChat();

  return (
    <>
      {/* <PushNotificationManager /> */}
      <InstallPrompt />
      <div className="flex flex-col h-full p-4 gap-4 pb-80">
        <Logo />
        <Chat messages={messages} addToolResult={addToolResult} />
        <ChatInput
          input={input}
          handleInputChange={handleInputChange}
          handleSubmit={handleSubmit}
        />
      </div>
    </>
  );
}
