"use client";
import { Loader2, PencilRuler } from "lucide-react";
import { FC, useState, useEffect } from "react";
import { ToolCallProps } from ".";

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
            result: JSON.stringify({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
            }),
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
      <div className="text-blue-600">
        {toolInvocation.state == "result" ? (
          <PencilRuler className="inline h-4 w-4 mr-1" />
        ) : (
          <Loader2 className="inline h-4 w-4 mr-1 animate-spin" />
        )}
        <span>{toolInvocation.toolName}</span>
      </div>
      {error && (
        <div className="text-red-600 mt-2">
          <p>Error: {error}</p>
        </div>
      )}
    </>
  );
};

export default UserLocationTool;
