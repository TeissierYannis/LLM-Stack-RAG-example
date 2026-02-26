import ReactMarkdown from "react-markdown";
import { FileText, User, Bot } from "lucide-react";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 p-4 ${isUser ? "bg-white" : "bg-gray-50"}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-700 text-white"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-500 mb-1">
          {isUser ? "Vous" : "Assistant"}
        </div>

        <div className="prose prose-sm max-w-none text-gray-800">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t pt-2">
            <div className="text-xs font-medium text-gray-500 mb-1">
              Sources :
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((src, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1 text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-md"
                  title={src.text_preview}
                >
                  <FileText size={12} />
                  <span>{src.filename}</span>
                  <span className="text-blue-400">
                    ({(src.score * 100).toFixed(0)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
