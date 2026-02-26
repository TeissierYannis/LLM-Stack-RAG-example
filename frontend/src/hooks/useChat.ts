import { useState, useCallback, useRef } from "react";
import { chatStreamSSE } from "../lib/api";
import type { Message, SourceReference } from "../types";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("default-completion");
  const [useRag, setUseRag] = useState(true);
  const cancelRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || isStreaming) return;

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
      };

      // Add placeholder for assistant
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        sources: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const cancel = chatStreamSSE(
        content,
        conversationId,
        selectedModel,
        useRag,
        {
          onMessage: (chunk) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + chunk,
                };
              }
              return updated;
            });
          },
          onSources: (sources: SourceReference[]) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = { ...last, sources };
              }
              return updated;
            });
          },
          onMeta: (meta) => {
            setConversationId(meta.conversation_id);
          },
          onDone: () => {
            setIsStreaming(false);
          },
          onError: (error) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: `Erreur: ${error}`,
                };
              }
              return updated;
            });
            setIsStreaming(false);
          },
        }
      );

      cancelRef.current = cancel;
    },
    [conversationId, selectedModel, useRag, isStreaming]
  );

  const stopStreaming = useCallback(() => {
    cancelRef.current?.();
    setIsStreaming(false);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  const loadConversation = useCallback(
    (id: string, msgs: Message[]) => {
      setConversationId(id);
      setMessages(msgs);
    },
    []
  );

  return {
    messages,
    isStreaming,
    conversationId,
    selectedModel,
    useRag,
    setSelectedModel,
    setUseRag,
    sendMessage,
    stopStreaming,
    clearChat,
    loadConversation,
  };
}
