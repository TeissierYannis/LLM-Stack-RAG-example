export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceReference[];
  created_at?: string;
}

export interface SourceReference {
  filename: string;
  chunk_index: number;
  score: number;
  text_preview: string;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  model: string;
  messages: Message[];
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  content_preview: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface ModelInfo {
  name: string;
  provider: string;
  model_type: string;
}

export interface ModelsResponse {
  completion_models: ModelInfo[];
  embedding_models: ModelInfo[];
}
