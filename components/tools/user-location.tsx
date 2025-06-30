"use client";
import { FC, useState, useEffect } from "react";
import { ToolCallProps } from ".";
import DefaultTool from "./default-tool";

const UserLocationTool: FC<ToolCallProps> = ({
  toolInvocation,
  addToolResult,
}) => {
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          addToolResult({
            toolCallId: toolInvocation.toolCallId,
            result: {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
            },
          });
        },
        (err) => {
          setError(err.message);
        },
      );
    } else {
      setError("Geolocation is not supported by your browser.");
    }
  }, [toolInvocation, addToolResult]);

  return (
    <>
      <DefaultTool
        toolInvocation={toolInvocation}
        addToolResult={addToolResult}
      />
      {error && (
        <div className="text-red-600 mt-2">
          <p>Error: {error}</p>
        </div>
      )}
    </>
  );
};

export default UserLocationTool;
