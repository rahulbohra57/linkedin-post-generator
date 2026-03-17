import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Draft, ImageResult } from "@/lib/api";

interface PostStore {
  sessionId: string | null;
  draftId: number | null;
  draft: Draft | null;
  images: ImageResult[];
  selectedImageId: string | null;
  setSessionId: (id: string) => void;
  setDraftId: (id: number) => void;
  setDraft: (draft: Draft) => void;
  setImages: (images: ImageResult[]) => void;
  setSelectedImageId: (id: string) => void;
  reset: () => void;
}

export const usePostStore = create<PostStore>()(
  persist(
    (set) => ({
      sessionId: null,
      draftId: null,
      draft: null,
      images: [],
      selectedImageId: null,

      setSessionId: (id) => set({ sessionId: id }),
      setDraftId: (id) => set({ draftId: id }),
      setDraft: (draft) => set({ draft }),
      setImages: (images) => set({ images }),
      setSelectedImageId: (id) => set({ selectedImageId: id }),
      reset: () =>
        set({
          draftId: null,
          draft: null,
          images: [],
          selectedImageId: null,
        }),
    }),
    { name: "post-store", partialize: (s) => ({ sessionId: s.sessionId, draftId: s.draftId }) }
  )
);
