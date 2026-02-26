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

export interface Assistant {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  model: string;
  embedding_model: string;
  qdrant_collection: string;
  avatar_color: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface AssistantCreate {
  name: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  avatar_color?: string;
}

export interface Conversation {
  id: string;
  assistant_id: string | null;
  assistant_name: string | null;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  assistant_id: string | null;
  title: string;
  model: string;
  messages: Message[];
}

export interface Document {
  id: string;
  assistant_id: string;
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

export interface OCRInfo {
  provider: string;
  provider_label: string;
  cloud_enabled: boolean;
}
