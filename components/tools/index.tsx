import { FC } from "react";
import { ToolInvocation } from "ai";
import DefaultTool from "./default-tool";

export const ToolCall: FC<ToolInvocation> = (toolInvocation) => {
  switch (toolInvocation.toolName) {
    default:
      return <DefaultTool {...toolInvocation} />;
  }
};
