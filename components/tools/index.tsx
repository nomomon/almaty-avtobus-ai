import { FC } from "react";
import { ToolInvocation } from "ai";
import DefaultTool from "./default-tool";
import UserLocationTool from "./user-location";

export interface ToolCallProps {
  toolInvocation: ToolInvocation;
  addToolResult: (result: { toolCallId: string; result: unknown }) => void;
}

export const ToolCall: FC<ToolCallProps> = (props) => {
  if (!props.toolInvocation.state) return null;

  switch (props.toolInvocation.toolName) {
    case "getUserLocation":
      return <UserLocationTool {...props} />;
    default:
      return <DefaultTool {...props} />;
  }
};
