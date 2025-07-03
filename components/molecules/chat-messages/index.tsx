import { UIMessage } from "ai";
import { FC } from "react";
import ReactMarkdown from "react-markdown";
import { ToolCall } from "../../tools";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "../../ui/avatar";

interface ChatMessagesProps {
  messages: UIMessage[];
  addToolResult: ({
    toolCallId,
    result,
  }: {
    toolCallId: string;
    result: unknown;
  }) => void;
}

const ChatMessages: FC<ChatMessagesProps> = ({ messages, addToolResult }) => {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn({
            "px-4 py-2 border rounded-md bg-zinc-600/10 flex flex-row gap-2":
              message.role === "user",
          })}
        >
          <div
            className={cn({
              hidden: message.role !== "user",
            })}
          >
            <Avatar>
              <AvatarImage src="" />
              <AvatarFallback className="bg-zinc-600 text-zinc-200 font-bold">
                {message.role[0].toLocaleUpperCase()}
              </AvatarFallback>
            </Avatar>
          </div>
          <div
            className={cn({
              "-my-2 translate-y-0.5": message.role === "user",
            })}
          >
            {message.parts.map((part, i) => (
              <div key={`${message.id}-${i}`} className="text-gray-800">
                {part.type === "text" && (
                  <div className="markdown-body">
                    <ReactMarkdown>{part.text}</ReactMarkdown>
                  </div>
                )}
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
  );
};

export default ChatMessages;
