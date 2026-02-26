import { useRef, useEffect } from "react";
import { useChat } from "./hooks/useChat";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import Sidebar from "./components/Sidebar";
import { Bot } from "lucide-react";

export default function App() {
  const {
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
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex h-screen">
      <Sidebar
        currentConversationId={conversationId}
        onNewChat={clearChat}
        onLoadConversation={loadConversation}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        useRag={useRag}
        onRagToggle={setUseRag}
      />

      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b bg-white px-6 py-3 flex items-center gap-3">
          <Bot size={24} className="text-blue-600" />
          <div>
            <h1 className="text-lg font-semibold text-gray-800">
              Enterprise Chat RAG
            </h1>
            <p className="text-xs text-gray-500">
              {selectedModel} | RAG {useRag ? "ON" : "OFF"}
            </p>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto scrollbar-thin"
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Bot size={48} className="mb-4" />
              <p className="text-lg">Posez une question</p>
              <p className="text-sm mt-1">
                Uploadez des documents pour activer le RAG
              </p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isStreaming && (
                <div className="p-4 text-sm text-gray-400 animate-pulse">
                  En cours de reflexion...
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopStreaming}
          isStreaming={isStreaming}
        />
      </div>
    </div>
  );
}
