import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useEnterSubmit } from "@/components/molecules/chat-input/index.hooks";
import { Send } from "lucide-react";
import { FC } from "react";

interface ChatInputProps {
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: () => void;
}

const ChatInput: FC<ChatInputProps> = ({
  input,
  handleInputChange,
  handleSubmit,
}) => {
  const { handleKeyDown } = useEnterSubmit();

  return (
    <div className="flex flex-row gap-4">
      <Textarea
        autoFocus
        value={input}
        onChange={handleInputChange}
        onKeyDown={(e) => handleKeyDown(e, handleSubmit)}
        placeholder="Сообщение..."
      />
      <Button className="h-8 w-8" onClick={handleSubmit}>
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
};

export default ChatInput;
