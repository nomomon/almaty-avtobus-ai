import { useCallback } from "react";

export function useEnterSubmit() {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>, onSubmit: () => void) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        onSubmit();
      }
    },
    [],
  );

  return { handleKeyDown };
}
