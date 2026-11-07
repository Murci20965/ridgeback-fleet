"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

interface ChatBridgeValue {
  pending: string | null;
  askChat: (question: string) => void;
  clearPending: () => void;
}

const ChatBridgeContext = createContext<ChatBridgeValue | null>(null);

export function useChatBridge() {
  const value = useContext(ChatBridgeContext);
  if (!value) throw new Error("useChatBridge must be used inside ChatBridge");
  return value;
}

/** Lets any part of the dashboard send a question to the chat panel. */
export function ChatBridge({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<string | null>(null);
  const clearPending = useCallback(() => setPending(null), []);
  const value = useMemo(
    () => ({ pending, askChat: setPending, clearPending }),
    [pending, clearPending],
  );
  return <ChatBridgeContext.Provider value={value}>{children}</ChatBridgeContext.Provider>;
}
