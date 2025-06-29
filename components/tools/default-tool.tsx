import { ToolInvocation } from "ai";
import { Loader2, PencilRuler } from "lucide-react";
import { FC } from "react";

const DefaultTool: FC<ToolInvocation> = (toolInvocation) => (
  <div className="text-blue-600">
    {toolInvocation.state == "result" ? (
      <PencilRuler className="inline h-4 w-4 mr-1" />
    ) : (
      <Loader2 className="inline h-4 w-4 mr-1 animate-spin" />
    )}
    <span>{toolInvocation.toolName}</span>
  </div>
);

export default DefaultTool;
