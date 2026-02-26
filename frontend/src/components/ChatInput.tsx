import { useState, useRef, useEffect } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

export default function ChatInput({ onSend, onStop, isStreaming }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (input.trim() && !isStreaming) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t bg-white p-4">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Posez votre question..."
          rows={1}
          className="flex-1 resize-none border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
        {isStreaming ? (
          <button
            onClick={onStop}
            className="flex-shrink-0 bg-red-600 text-white rounded-lg p-3 hover:bg-red-700 transition"
          >
            <Square size={18} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!input.trim()}
            className="flex-shrink-0 bg-blue-600 text-white rounded-lg p-3 hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
