const API_BASE = "/api";

export async function fetchConversations() {
  const res = await fetch(`${API_BASE}/conversations`);
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

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload document");
  return res.json();
}

export async function deleteDocument(id: string) {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
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

export interface ChatStreamCallbacks {
  onMessage: (chunk: string) => void;
  onSources: (sources: any[]) => void;
  onMeta: (meta: { conversation_id: string }) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export async function chatStream(
  message: string,
  conversationId: string | null,
  model: string | null,
  useRag: boolean,
  callbacks: ChatStreamCallbacks
) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      model,
      use_rag: useRag,
    }),
  });

  if (!res.ok) {
    callbacks.onError(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        const event = line.slice(7).trim();
        // Next line should be data
        continue;
      }
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        // Determine event type from previous event line
        // SSE format: event line then data line
        // We need to track the current event
        continue;
      }

      // Parse combined event+data
      if (line.includes("event:") || line.includes("data:")) continue;
    }
  }

  // Simpler SSE parsing approach
  callbacks.onDone();
}

// More robust SSE parser
export function chatStreamSSE(
  message: string,
  conversationId: string | null,
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
