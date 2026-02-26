import type { AssistantCreate } from "../types";

const API_BASE = "/api";

// --- Assistants ---
export async function fetchAssistants() {
  const res = await fetch(`${API_BASE}/assistants`);
  if (!res.ok) throw new Error("Failed to fetch assistants");
  return res.json();
}

export async function fetchAssistant(id: string) {
  const res = await fetch(`${API_BASE}/assistants/${id}`);
  if (!res.ok) throw new Error("Failed to fetch assistant");
  return res.json();
}

export async function createAssistant(data: AssistantCreate) {
  const res = await fetch(`${API_BASE}/assistants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create assistant");
  return res.json();
}

export async function updateAssistant(id: string, data: Partial<AssistantCreate>) {
  const res = await fetch(`${API_BASE}/assistants/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update assistant");
  return res.json();
}

export async function deleteAssistant(id: string) {
  const res = await fetch(`${API_BASE}/assistants/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete assistant");
  return res.json();
}

// --- Conversations ---
export async function fetchConversations(assistantId?: string) {
  const params = assistantId ? `?assistant_id=${assistantId}` : "";
  const res = await fetch(`${API_BASE}/conversations${params}`);
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function fetchConversation(id: string) {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export async function deleteConversation(id: string) {
  const res = await fetch(`${API_BASE}/conversations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
  return res.json();
}

// --- Documents (scoped per assistant) ---
export async function fetchDocuments(assistantId: string) {
  const res = await fetch(`${API_BASE}/assistants/${assistantId}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocument(assistantId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/assistants/${assistantId}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload document");
  return res.json();
}

export async function deleteDocument(assistantId: string, docId: string) {
  const res = await fetch(`${API_BASE}/assistants/${assistantId}/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete document");
  return res.json();
}

export async function fetchModels() {
  const res = await fetch(`${API_BASE}/models`);
  if (!res.ok) throw new Error("Failed to fetch models");
  return res.json();
}

export async function fetchOCRInfo() {
  const res = await fetch(`${API_BASE}/models/ocr`);
  if (!res.ok) throw new Error("Failed to fetch OCR info");
  return res.json();
}

export interface ChatStreamCallbacks {
  onMessage: (chunk: string) => void;
  onSources: (sources: any[]) => void;
  onMeta: (meta: { conversation_id: string }) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export function chatStreamSSE(
  message: string,
  conversationId: string | null,
  assistantId: string | null,
  model: string | null,
  useRag: boolean,
  callbacks: ChatStreamCallbacks
): () => void {
  const abortController = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          assistant_id: assistantId,
          model,
          use_rag: useRag,
        }),
        signal: abortController.signal,
      });

      if (!res.ok) {
        callbacks.onError(`HTTP ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "message";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = line.slice(6);

            switch (currentEvent) {
              case "message":
                callbacks.onMessage(data);
                break;
              case "sources":
                try {
                  callbacks.onSources(JSON.parse(data));
                } catch {}
                break;
              case "meta":
                try {
                  callbacks.onMeta(JSON.parse(data));
                } catch {}
                break;
              case "done":
                callbacks.onDone();
                break;
              case "error":
                callbacks.onError(data);
                break;
            }
            currentEvent = "message"; // reset
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        callbacks.onError(err.message);
      }
    }
  })();

  return () => abortController.abort();
}
