import { useState, useEffect } from "react";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import {
  fetchConversations,
  fetchConversation,
  deleteConversation,
} from "../lib/api";
import AssistantPanel from "./AssistantPanel";
import type { Assistant, Conversation, Message } from "../types";

interface Props {
  currentConversationId: string | null;
  activeAssistant: Assistant | null;
  onNewChat: () => void;
  onLoadConversation: (id: string, messages: Message[]) => void;
  onSelectAssistant: (assistant: Assistant | null) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  useRag: boolean;
  onRagToggle: (enabled: boolean) => void;
}

export default function Sidebar({
  currentConversationId,
  activeAssistant,
  onNewChat,
  onLoadConversation,
  onSelectAssistant,
  selectedModel,
  onModelChange,
  useRag,
  onRagToggle,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    loadConversations();
  }, [currentConversationId, activeAssistant?.id]);

  async function loadConversations() {
    try {
      const data = await fetchConversations(activeAssistant?.id);
      setConversations(data);
    } catch {}
  }

  async function handleLoadConversation(id: string) {
    try {
      const data = await fetchConversation(id);
      onLoadConversation(id, data.messages);
    } catch {}
  }

  async function handleDeleteConversation(id: string) {
    try {
      await deleteConversation(id);
      loadConversations();
      if (id === currentConversationId) onNewChat();
    } catch {}
  }

  return (
    <div className="w-80 bg-gray-900 text-white flex flex-col h-full">
      {/* New Chat */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-600 hover:bg-gray-800 transition text-sm"
        >
          <MessageSquarePlus size={16} />
          Nouvelle conversation
        </button>
      </div>

      {/* Model selector (only when no assistant) */}
      {!activeAssistant && (
        <div className="px-3 pb-2">
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="w-full bg-gray-800 text-white text-xs rounded-md px-2 py-1.5 border border-gray-700"
          >
            <option value="default-completion">Auto (load-balanced)</option>
            <option value="claude-sonnet">Claude Sonnet (Bedrock)</option>
            <option value="gpt-4o">GPT-4o (Azure Foundry)</option>
            <option value="gemini-flash">Gemini Flash (Vertex)</option>
          </select>
        </div>
      )}

      {/* RAG toggle (only when no assistant - assistant always uses RAG) */}
      {!activeAssistant && (
        <div className="px-3 pb-3 flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => onRagToggle(e.target.checked)}
              className="rounded"
            />
            RAG (documents)
          </label>
        </div>
      )}

      {/* Assistants panel */}
      <div className="border-t border-gray-700 flex-shrink-0 max-h-[45%] overflow-y-auto">
        <AssistantPanel
          activeAssistant={activeAssistant}
          onSelect={onSelectAssistant}
        />
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 border-t border-gray-700 pt-1">
        <div className="text-xs text-gray-400 px-2 py-1 uppercase tracking-wider">
          Conversations
          {activeAssistant && (
            <span className="normal-case ml-1">
              ({activeAssistant.name})
            </span>
          )}
        </div>
        {conversations.length === 0 && (
          <p className="text-xs text-gray-600 px-2 py-2">
            Aucune conversation
          </p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`flex items-center gap-1 px-2 py-2 rounded-md cursor-pointer text-sm group ${
              conv.id === currentConversationId
                ? "bg-gray-700"
                : "hover:bg-gray-800"
            }`}
            onClick={() => handleLoadConversation(conv.id)}
          >
            <span className="flex-1 truncate">{conv.title}</span>
            {conv.assistant_name && !activeAssistant && (
              <span className="text-xs text-gray-500 flex-shrink-0">
                {conv.assistant_name}
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteConversation(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
