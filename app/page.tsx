"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";
import { useEnterSubmit } from "@/lib/hooks/use-enter-submit";
import Chat from "@/components/templates/chat";
import Logo from "@/components/atoms/logo";
import { useState, useEffect } from "react";

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

function PushNotificationManager() {
    const [isSupported, setIsSupported] = useState(false);
    const [subscription, setSubscription] = useState<PushSubscription | null>(null);
    const [message, setMessage] = useState("");

    useEffect(() => {
        if ("serviceWorker" in navigator && "PushManager" in window) {
            setIsSupported(true);
            registerServiceWorker();
        }
    }, []);

    async function registerServiceWorker() {
        const registration = await navigator.serviceWorker.register("/sw.js", {
            scope: "/",
            updateViaCache: "none",
        });
        const sub = await registration.pushManager.getSubscription();
        setSubscription(sub);
    }

    async function subscribeToPush() {
        const registration = await navigator.serviceWorker.ready;
        const sub = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(
                process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!
            ),
        });
        setSubscription(sub);
        const serializedSub = JSON.parse(JSON.stringify(sub));
        const { subscribeUser } = await import("./actions");
        await subscribeUser(serializedSub);
    }

    async function unsubscribeFromPush() {
        await subscription?.unsubscribe();
        setSubscription(null);
        const { unsubscribeUser } = await import("./actions");
        await unsubscribeUser();
    }

    async function sendTestNotification() {
        if (subscription) {
            const { sendNotification } = await import("./actions");
            await sendNotification(message);
            setMessage("");
        }
    }

    if (!isSupported) {
        return <p>Push notifications are not supported in this browser.</p>;
    }

    return (
        <div>
            <h3>Push Notifications</h3>
            {subscription ? (
                <>
                    <p>You are subscribed to push notifications.</p>
                    <button onClick={unsubscribeFromPush}>Unsubscribe</button>
                    <input
                        type="text"
                        placeholder="Enter notification message"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                    />
                    <button onClick={sendTestNotification}>Send Test</button>
                </>
            ) : (
                <>
                    <p>You are not subscribed to push notifications.</p>
                    <button onClick={subscribeToPush}>Subscribe</button>
                </>
            )}
        </div>
    );
}

function InstallPrompt() {
    const [isIOS, setIsIOS] = useState(false);
    const [isStandalone, setIsStandalone] = useState(false);

    useEffect(() => {
        setIsIOS(
            /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream
        );
        setIsStandalone(window.matchMedia("(display-mode: standalone)").matches);
    }, []);

    if (isStandalone) {
        return null;
    }

    return (
        <div>
            <h3>Install App</h3>
            <button>Add to Home Screen</button>
            {isIOS && (
                <p>
                    To install this app on your iOS device, tap the share button
                    <span role="img" aria-label="share icon">
                        {" "}
                        ⎋{" "}
                    </span>
                    and then "Add to Home Screen"
                    <span role="img" aria-label="plus icon">
                        {" "}
                        ➕{" "}
                    </span>
                    .
                </p>
            )}
        </div>
    );
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
