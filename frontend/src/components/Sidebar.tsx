import { useState, useEffect } from "react";
import {
  MessageSquarePlus,
  Trash2,
  FileUp,
  FileText,
  Settings,
  X,
} from "lucide-react";
import {
  fetchConversations,
  fetchConversation,
  deleteConversation,
  fetchDocuments,
  uploadDocument,
  deleteDocument,
} from "../lib/api";
import type { Conversation, Document, Message } from "../types";

interface Props {
  currentConversationId: string | null;
  onNewChat: () => void;
  onLoadConversation: (id: string, messages: Message[]) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  useRag: boolean;
  onRagToggle: (enabled: boolean) => void;
}

export default function Sidebar({
  currentConversationId,
  onNewChat,
  onLoadConversation,
  selectedModel,
  onModelChange,
  useRag,
  onRagToggle,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [showDocs, setShowDocs] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadConversations();
    loadDocuments();
  }, [currentConversationId]);

  async function loadConversations() {
    try {
      const data = await fetchConversations();
      setConversations(data);
    } catch {}
  }

  async function loadDocuments() {
    try {
      const data = await fetchDocuments();
      setDocuments(data);
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

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      loadDocuments();
    } catch {}
    setUploading(false);
    e.target.value = "";
  }

  async function handleDeleteDoc(id: string) {
    try {
      await deleteDocument(id);
      loadDocuments();
    } catch {}
  }

  return (
    <div className="w-72 bg-gray-900 text-white flex flex-col h-full">
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

      {/* Model selector */}
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

      {/* RAG toggle */}
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

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-2">
        <div className="text-xs text-gray-400 px-2 py-1 uppercase tracking-wider">
          Conversations
        </div>
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

      {/* Documents section */}
      <div className="border-t border-gray-700">
        <button
          onClick={() => setShowDocs(!showDocs)}
          className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-800"
        >
          <FileText size={16} />
          Documents ({documents.length})
          <span className="ml-auto text-xs text-gray-400">
            {showDocs ? "masquer" : "afficher"}
          </span>
        </button>

        {showDocs && (
          <div className="px-3 pb-3 max-h-48 overflow-y-auto">
            {/* Upload */}
            <label className="flex items-center gap-2 px-2 py-1.5 mb-1 rounded-md bg-gray-800 hover:bg-gray-700 cursor-pointer text-xs">
              <FileUp size={14} />
              {uploading ? "Upload en cours..." : "Uploader un fichier"}
              <input
                type="file"
                accept=".pdf,.docx,.md,.txt"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>

            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-1 px-2 py-1 text-xs group"
              >
                <FileText size={12} className="text-gray-400 flex-shrink-0" />
                <span className="truncate flex-1">{doc.filename}</span>
                <span
                  className={`text-xs ${
                    doc.status === "ready"
                      ? "text-green-400"
                      : doc.status === "error"
                        ? "text-red-400"
                        : "text-yellow-400"
                  }`}
                >
                  {doc.status === "ready"
                    ? `${doc.chunk_count}ch`
                    : doc.status}
                </span>
                <button
                  onClick={() => handleDeleteDoc(doc.id)}
                  className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
