"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";
import { useEnterSubmit } from "@/lib/hooks/use-enter-submit";
import Chat from "@/components/templates/chat";
import Logo from "@/components/atoms/logo";
import PushNotificationManager from "@/components/atoms/push-notification-manager";
import InstallPrompt from "@/components/atoms/install-prompt";

function urlBase64ToUint8Array(base64String: string) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

export default function Home() {
    const { messages, input, handleInputChange, handleSubmit, addToolResult } =
        useChat();
    const { handleKeyDown } = useEnterSubmit();

    return (
        <div className="flex flex-col min-h-screen p-4 gap-4 pb-80">
            <Logo />
            <Chat messages={messages} addToolResult={addToolResult} />
            <PushNotificationManager />
            <InstallPrompt />
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
