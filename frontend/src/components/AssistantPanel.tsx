import { useState, useEffect } from "react";
import {
  Plus,
  Trash2,
  FileUp,
  FileText,
  X,
  Save,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import {
  fetchAssistants,
  createAssistant,
  deleteAssistant,
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  fetchOCRInfo,
} from "../lib/api";
import type { Assistant, Document, OCRInfo } from "../types";

interface Props {
  activeAssistant: Assistant | null;
  onSelect: (assistant: Assistant | null) => void;
}

const COLORS = [
  "#3b82f6",
  "#ef4444",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
];

export default function AssistantPanel({ activeAssistant, onSelect }: Props) {
  const [assistants, setAssistants] = useState<Assistant[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Record<string, Document[]>>({});
  const [uploading, setUploading] = useState(false);
  const [ocrInfo, setOcrInfo] = useState<OCRInfo | null>(null);

  // Create form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState(
    "Tu es un assistant d'entreprise intelligent. Réponds de manière précise et concise en te basant sur le contexte fourni."
  );
  const [model, setModel] = useState("default-completion");
  const [color, setColor] = useState(COLORS[0]);

  useEffect(() => {
    loadAssistants();
    fetchOCRInfo().then(setOcrInfo).catch(() => {});
  }, []);

  async function loadAssistants() {
    try {
      const data = await fetchAssistants();
      setAssistants(data);
    } catch {}
  }

  async function loadDocs(assistantId: string) {
    try {
      const data = await fetchDocuments(assistantId);
      setDocuments((prev) => ({ ...prev, [assistantId]: data }));
    } catch {}
  }

  async function handleCreate() {
    if (!name.trim()) return;
    try {
      const created = await createAssistant({
        name,
        description: description || undefined,
        system_prompt: systemPrompt,
        model,
        avatar_color: color,
      });
      setAssistants((prev) => [created, ...prev]);
      setShowCreate(false);
      setName("");
      setDescription("");
      onSelect(created);
    } catch {}
  }

  async function handleDelete(id: string) {
    try {
      await deleteAssistant(id);
      setAssistants((prev) => prev.filter((a) => a.id !== id));
      if (activeAssistant?.id === id) onSelect(null);
    } catch {}
  }

  async function handleUpload(
    assistantId: string,
    e: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(assistantId, file);
      loadDocs(assistantId);
      loadAssistants();
    } catch {}
    setUploading(false);
    e.target.value = "";
  }

  async function handleDeleteDoc(assistantId: string, docId: string) {
    try {
      await deleteDocument(assistantId, docId);
      loadDocs(assistantId);
      loadAssistants();
    } catch {}
  }

  function toggleExpand(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
      if (!documents[id]) loadDocs(id);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wider">
          Assistants
        </span>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-gray-400 hover:text-white"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="px-3 pb-3 space-y-2 border-b border-gray-700">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nom de l'assistant"
            className="w-full bg-gray-800 text-white text-xs rounded-md px-2 py-1.5 border border-gray-700"
          />
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optionnel)"
            className="w-full bg-gray-800 text-white text-xs rounded-md px-2 py-1.5 border border-gray-700"
          />
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="System prompt"
            rows={3}
            className="w-full bg-gray-800 text-white text-xs rounded-md px-2 py-1.5 border border-gray-700 resize-none"
          />
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full bg-gray-800 text-white text-xs rounded-md px-2 py-1.5 border border-gray-700"
          >
            <option value="default-completion">Auto (load-balanced)</option>
            <option value="claude-sonnet">Claude Sonnet (Bedrock)</option>
            <option value="gpt-4o">GPT-4o (Azure Foundry)</option>
            <option value="gemini-flash">Gemini Flash (Vertex)</option>
          </select>
          <div className="flex gap-1">
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-5 h-5 rounded-full ${
                  color === c ? "ring-2 ring-white ring-offset-1 ring-offset-gray-900" : ""
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!name.trim()}
              className="flex-1 flex items-center justify-center gap-1 bg-blue-600 text-white text-xs rounded-md px-2 py-1.5 hover:bg-blue-700 disabled:opacity-50"
            >
              <Save size={12} />
              Creer
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-2 py-1.5 text-gray-400 text-xs hover:text-white"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Assistant list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 py-1">
        {/* "No assistant" option */}
        <div
          onClick={() => onSelect(null)}
          className={`flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-sm mb-1 ${
            !activeAssistant ? "bg-gray-700" : "hover:bg-gray-800"
          }`}
        >
          <div className="w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center text-xs">
            ?
          </div>
          <span className="text-gray-300">Chat libre (sans assistant)</span>
        </div>

        {assistants.map((a) => (
          <div key={a.id} className="mb-1">
            <div
              className={`flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-sm group ${
                activeAssistant?.id === a.id ? "bg-gray-700" : "hover:bg-gray-800"
              }`}
              onClick={() => onSelect(a)}
            >
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs text-white font-bold flex-shrink-0"
                style={{ backgroundColor: a.avatar_color }}
              >
                {a.name[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="truncate">{a.name}</div>
                <div className="text-xs text-gray-500">
                  {a.document_count} doc{a.document_count !== 1 ? "s" : ""}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(a.id);
                }}
                className="text-gray-500 hover:text-gray-300"
              >
                {expandedId === a.id ? (
                  <ChevronDown size={14} />
                ) : (
                  <ChevronRight size={14} />
                )}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(a.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400"
              >
                <Trash2 size={14} />
              </button>
            </div>

            {/* Expanded: documents */}
            {expandedId === a.id && (
              <div className="ml-4 pl-4 border-l border-gray-700 py-1">
                {a.description && (
                  <p className="text-xs text-gray-500 mb-1 italic">
                    {a.description}
                  </p>
                )}
                <label className="flex items-center gap-1 px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 cursor-pointer text-xs mb-1">
                  <FileUp size={12} />
                  {uploading ? "Upload..." : "Ajouter un document"}
                  <input
                    type="file"
                    accept=".pdf,.docx,.md,.txt,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif"
                    onChange={(e) => handleUpload(a.id, e)}
                    className="hidden"
                    disabled={uploading}
                  />
                </label>
                {ocrInfo && (
                  <div className={`text-[10px] px-2 py-0.5 mb-1 ${ocrInfo.cloud_enabled ? "text-cyan-400" : "text-gray-500"}`}>
                    OCR: {ocrInfo.provider_label}
                  </div>
                )}
                {(documents[a.id] || []).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-1 px-2 py-0.5 text-xs group/doc"
                  >
                    <FileText
                      size={11}
                      className="text-gray-500 flex-shrink-0"
                    />
                    <span className="truncate flex-1 text-gray-400">
                      {doc.filename}
                    </span>
                    <span
                      className={`${
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
                      onClick={() => handleDeleteDoc(a.id, doc.id)}
                      className="opacity-0 group-hover/doc:opacity-100 text-gray-500 hover:text-red-400"
                    >
                      <X size={11} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
