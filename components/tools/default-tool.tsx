import {
  BusFront,
  ChevronDown,
  LetterText,
  Loader2,
  MapPinCheck,
  PencilRuler,
} from "lucide-react";
import React, { FC, useState } from "react";
import { ToolCallProps } from ".";
import { ToolInvocation } from "ai";
import { cn } from "@/lib/utils";

const toolNameToIcon: Record<string, FC<{ size?: number }>> = {
  getPointDescription: LetterText,
  getTransitData: BusFront,
  getUserLocation: MapPinCheck,
};

const renderIcon = (toolInvocation: ToolInvocation) => {
  if (toolInvocation.state !== "result") {
    return <Loader2 size={16} className=" animate-spin" />;
  }

  const IconComponent = toolNameToIcon[toolInvocation.toolName] ?? PencilRuler;

  return <IconComponent size={16} />;
};

const DefaultTool: FC<ToolCallProps> = ({ toolInvocation }) => {
  const [open, setOpen] = useState(false);

  const handleClick = () => {
    setOpen((o) => !o);
  };

  return (
    <div className="my-2 border rounded-sm bg-muted flex flex-col">
      <button
        onClick={handleClick}
        className="py-2 px-3 flex flex-row items-center justify-between cursor-pointer w-full text-left"
      >
        <div className="flex flex-row items-center gap-2">
          <div className="flex items-center justify-center w-5 h-5 text-muted-foreground/80">
            {renderIcon(toolInvocation)}
          </div>
          <span className="text-sm text-muted-foreground">
            {toolInvocation.args?.description ?? toolInvocation.toolName}
          </span>
        </div>
        <div className="text-muted-foreground/80">
          <ChevronDown
            size={16}
            className={cn(
              "transition-transform",
              open ? "rotate-180" : "rotate-360",
            )}
          />
        </div>
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-300",
          open ? "max-h-96" : "max-h-0",
        )}
      >
        <div className="py-2 px-3 border-t">
          {toolInvocation.state === "result" ? (
            <pre className="text-sm text-muted-foreground">
              {JSON.stringify(toolInvocation.result, null, 2)}
            </pre>
          ) : (
            <div className="text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              <span>Loading...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DefaultTool;
