import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default api;

// --- Types ---
export interface GenerateRequest {
  topic: string;
  tone: "professional" | "conversational" | "thought_leader" | "educational" | "inspirational";
  target_audience: string;
  post_length: "short" | "medium" | "long";
  session_id: string;
}

export interface GenerateResponse {
  draft_id: number;
  session_id: string;
  status: string;
  message: string;
}

export interface Draft {
  id: number;
  topic: string;
  tone: string;
  target_audience: string | null;
  post_text: string | null;
  hashtags: string | null;
  quality_score: number | null;
  quality_notes: string | null;
  character_count: number | null;
  selected_image_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ImageResult {
  id: string;
  url: string;
  thumbnail_url: string;
  source: "ai_generated" | "stock" | "uploaded";
  prompt?: string;
  photographer?: string;
  recommended: boolean;
  recommendation_reason?: string;
}

export interface ImageListResponse {
  images: ImageResult[];
  recommended_id: string | null;
}

// --- API helpers ---
export const generatePost = (req: GenerateRequest) =>
  api.post<GenerateResponse>("/generate", req).then((r) => r.data);

export const getDraft = (id: number) =>
  api.get<Draft>(`/drafts/${id}`).then((r) => r.data);

export const updateDraft = (id: number, data: Partial<Pick<Draft, "post_text" | "selected_image_url">>) =>
  api.patch<Draft>(`/drafts/${id}`, data).then((r) => r.data);

export const getImages = (draft_id: number, session_id: string, search_query?: string) =>
  api
    .get<ImageListResponse>(`/images`, { params: { draft_id, session_id, search_query } })
    .then((r) => r.data);

export const uploadImage = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<ImageResult>("/images/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

