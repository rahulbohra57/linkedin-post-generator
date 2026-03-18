"use client";
import { useEffect, useState, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle,
  Loader2,
  AlertCircle,
  ChevronRight,
  Image as ImageIcon,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { getDraft, updateDraft, getImages, type ImageResult } from "@/lib/api";
import { usePostStore } from "@/store/postStore";
import { getOrCreateSessionId } from "@/lib/utils";

const AGENT_NAMES = [
  "Researcher",
  "Tone Analyzer",
  "Writer",
  "Editor",
  "Hashtag Researcher",
  "Post Assembler",
  "Pexels Image Searcher",
  "Gemini Verifier",
];

// How often to poll draft status when WebSocket fails
const POLL_INTERVAL_MS = 3000;

function GeneratePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftId = Number(searchParams.get("draft_id"));
  const sessionId = getOrCreateSessionId();

  const { setDraft, setImages, setSelectedImageId, selectedImageId, images: storeImages } = usePostStore();

  // Post state
  const [postText, setPostText] = useState("");
  const [charCount, setCharCount] = useState(0);
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [qualityNotes, setQualityNotes] = useState<string[]>([]);
  const [completedAgents, setCompletedAgents] = useState<Set<string>>(new Set());
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);

  // True when the post is fully ready (either via WS or polling)
  const [postReady, setPostReady] = useState(false);

  // Image section state
  const [localImages, setLocalImages] = useState<ImageResult[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const [imageSearch, setImageSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState<string | null>(null);

  // Navigation
  const [saving, setSaving] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // True if the draft is already done when the page first loads (e.g. "Back to edit")
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // ── Load post content from draft ─────────────────────────────────────────
  const loadDraft = useCallback(async () => {
    if (!draftId) return;
    const draft = await getDraft(draftId);
    setDraft(draft);
    if (draft.post_text) {
      setPostText(draft.post_text);
      setCharCount(draft.post_text.length);
    }
    if (draft.quality_score != null) setQualityScore(draft.quality_score);
    if (draft.quality_notes) {
      setQualityNotes(draft.quality_notes.split("\n").filter(Boolean));
    }
    return draft;
  }, [draftId, setDraft]);

  // ── On mount: check if draft is already ready (back-navigation case) ──────
  useEffect(() => {
    if (!draftId) return;
    getDraft(draftId).then((draft) => {
      if (draft.status === "ready") {
        setDraft(draft);
        if (draft.post_text) {
          setPostText(draft.post_text);
          setCharCount(draft.post_text.length);
        }
        if (draft.quality_score != null) setQualityScore(draft.quality_score);
        if (draft.quality_notes) {
          setQualityNotes(draft.quality_notes.split("\n").filter(Boolean));
        }
        setCompletedAgents(new Set(AGENT_NAMES));
        setPostReady(true);
      }
      // Restore images from store if they were already loaded
      if (storeImages.length > 0) {
        setLocalImages(storeImages);
        setImagesLoaded(true);
      }
      setInitialCheckDone(true);
    });
  }, [draftId]);

  // Only connect WebSocket if the draft isn't already ready
  const { events, isDone, error } = useWebSocket(sessionId, !!draftId && initialCheckDone && !postReady);

  // ── Process WebSocket events ──────────────────────────────────────────────
  useEffect(() => {
    for (const event of events) {
      if (event.event === "agent_start") {
        setCurrentAgent(event.agent);
      } else if (event.event === "agent_complete") {
        setCompletedAgents((prev) => new Set([...prev, event.agent]));
        setCurrentAgent(null);
      } else if (event.event === "pipeline_done") {
        setPostText(event.post_text);
        setCharCount(event.post_text.length);
        setQualityScore(event.quality_score);
        setCurrentAgent(null);
      }
    }
  }, [events]);

  // When WS signals done, load full draft (has quality notes etc.)
  useEffect(() => {
    if (!isDone || !draftId) return;
    loadDraft().then(() => setPostReady(true));
    // Mark all agents as done in case some agent_complete events were missed
    setCompletedAgents(new Set(AGENT_NAMES));
  }, [isDone, draftId]);

  // ── Fallback polling when WebSocket errors ───────────────────────────────
  // If there's a WS error and post isn't ready yet, poll the draft API
  useEffect(() => {
    if (!error || postReady || !draftId) return;

    const poll = async () => {
      try {
        const draft = await getDraft(draftId);
        if (draft.status === "ready") {
          setDraft(draft);
          if (draft.post_text) {
            setPostText(draft.post_text);
            setCharCount(draft.post_text.length);
          }
          if (draft.quality_score != null) setQualityScore(draft.quality_score);
          if (draft.quality_notes) {
            setQualityNotes(draft.quality_notes.split("\n").filter(Boolean));
          }
          setCompletedAgents(new Set(AGENT_NAMES));
          setPostReady(true);
          return true; // stop polling
        }
        if (draft.status === "error") {
          setPipelineError("Post generation failed. Please go back and try again.");
          return true;
        }
      } catch {}
      return false;
    };

    let timer: ReturnType<typeof setTimeout>;
    const run = async () => {
      const done = await poll();
      if (!done) timer = setTimeout(run, POLL_INTERVAL_MS);
    };
    run();
    return () => clearTimeout(timer);
  }, [error, postReady, draftId]);

  // ── Image fetching ────────────────────────────────────────────────────────
  const fetchImages = useCallback(
    async (query?: string) => {
      if (!draftId) return;
      setImagesLoading(true);
      try {
        const result = await getImages(draftId, sessionId, query || undefined);
        setImages(result.images);    // sync to store so preview page can find selected image URL
        setLocalImages(result.images);
        if (result.recommended_id) setSelectedImageId(result.recommended_id);
        setImagesLoaded(true);
      } catch (e) {
        console.error("Pexels fetch failed:", e);
      } finally {
        setImagesLoading(false);
      }
    },
    [draftId, sessionId, setSelectedImageId]
  );

  const handleImageSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = imageSearch.trim();
    if (!q) return;
    setActiveSearch(q);
    fetchImages(q);
  };

  const handleClearSearch = () => {
    setActiveSearch(null);
    setImageSearch("");
    fetchImages();
  };

  // ── Continue to preview ───────────────────────────────────────────────────
  const handleContinue = async () => {
    setSaving(true);
    await updateDraft(draftId, { post_text: postText });
    setSaving(false);
    router.push(`/preview?draft_id=${draftId}`);
  };

  const completedCount = completedAgents.size;
  const progress = Math.round((completedCount / AGENT_NAMES.length) * 100);
  const isReady = postReady || (isDone && !error);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Generating Your Post</h2>
        <p className="text-gray-500">8 AI agents are working together to craft your LinkedIn post.</p>
      </div>

      {/* ── Row 1: Agent progress + Post editor ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent progress */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Agent Progress</h3>
            <span className="text-sm text-gray-400">{completedCount}/{AGENT_NAMES.length} done</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5 mb-5">
            <div
              className="bg-linkedin-blue h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="space-y-3">
            {AGENT_NAMES.map((agent) => {
              const isComplete = completedAgents.has(agent);
              const isRunning = currentAgent === agent;
              return (
                <div key={agent} className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    {isComplete ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : isRunning ? (
                      <Loader2 className="w-5 h-5 text-linkedin-blue animate-spin" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
                    )}
                  </div>
                  <span className={`text-sm font-medium ${
                    isComplete ? "text-gray-700" : isRunning ? "text-linkedin-blue" : "text-gray-400"
                  }`}>
                    {agent}
                  </span>
                  {isRunning && (
                    <span className="text-xs text-linkedin-blue bg-linkedin-blue-light px-2 py-0.5 rounded-full">
                      running
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Pipeline failure error */}
          {pipelineError && (
            <div className="mt-4 flex items-start gap-2 bg-red-50 text-red-700 p-3 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{pipelineError}</span>
            </div>
          )}
          {/* Only show WS error if post is not yet ready and no pipeline error */}
          {error && !isReady && !pipelineError && (
            <div className="mt-4 flex items-start gap-2 bg-yellow-50 text-yellow-700 p-3 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>Live updates unavailable — checking for completion…</span>
            </div>
          )}
        </div>

        {/* Post editor */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-800">Post Preview</h3>
            {qualityScore !== null && (
              <div className={`text-sm font-semibold px-2 py-1 rounded-lg ${
                qualityScore >= 8 ? "bg-green-50 text-green-700" :
                qualityScore >= 6 ? "bg-yellow-50 text-yellow-700" :
                "bg-red-50 text-red-700"
              }`}>
                {qualityScore.toFixed(1)}/10
              </div>
            )}
          </div>

          {!isReady ? (
            <div className="min-h-[300px] flex flex-col items-center justify-center text-gray-400">
              <Loader2 className="w-8 h-8 animate-spin mb-3 text-linkedin-blue" />
              <p className="text-sm">
                {currentAgent ? `${currentAgent} is working…` : "Waiting for agents…"}
              </p>
            </div>
          ) : (
            <>
              <textarea
                className="w-full border border-gray-200 rounded-xl p-4 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-linkedin-blue resize-none"
                rows={12}
                value={postText}
                onChange={(e) => { setPostText(e.target.value); setCharCount(e.target.value.length); }}
              />
              <div className="flex items-center justify-between mt-2">
                <div className={`text-xs font-medium ${charCount > 2800 ? "text-red-500" : "text-gray-400"}`}>
                  {charCount} / 3000 characters
                </div>
                <div className="w-24 bg-gray-100 rounded-full h-1">
                  <div
                    className={`h-1 rounded-full transition-all ${charCount > 2800 ? "bg-red-400" : "bg-linkedin-blue"}`}
                    style={{ width: `${Math.min((charCount / 3000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              {qualityNotes.length > 0 && (
                <div className="mt-3 space-y-1">
                  {qualityNotes.map((note, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-xs text-gray-500">
                      <span className="text-linkedin-blue mt-0.5">•</span>
                      {note}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Row 2: Image selection (shown after post is ready) ── */}
      {isReady && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-800">Choose an Image</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Pick a Pexels photo to accompany your post, or skip and go text-only.
              </p>
            </div>
            {imagesLoaded && (
              <button
                onClick={() => fetchImages(activeSearch || undefined)}
                disabled={imagesLoading}
                className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-linkedin-blue transition-colors disabled:opacity-40"
              >
                <RefreshCw className={`w-4 h-4 ${imagesLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            )}
          </div>

          {/* Not yet loaded → big CTA button */}
          {!imagesLoaded && !imagesLoading && (
            <button
              onClick={() => fetchImages()}
              className="w-full py-4 rounded-xl border-2 border-dashed border-linkedin-blue text-linkedin-blue font-semibold flex items-center justify-center gap-2 hover:bg-linkedin-blue-light transition-colors"
            >
              <ImageIcon className="w-5 h-5" />
              Generate Image Suggestions from Pexels
            </button>
          )}

          {/* Loading */}
          {imagesLoading && (
            <div className="flex items-center justify-center py-12 text-gray-400 gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-linkedin-blue" />
              <span className="text-sm">
                {activeSearch ? `Searching for "${activeSearch}"…` : "Finding relevant photos on Pexels…"}
              </span>
            </div>
          )}

          {/* Images loaded */}
          {imagesLoaded && !imagesLoading && (
            <div className="space-y-4">
              {/* Search bar */}
              <form onSubmit={handleImageSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                  <input
                    type="text"
                    value={imageSearch}
                    onChange={(e) => setImageSearch(e.target.value)}
                    placeholder="Search Pexels for a different image…"
                    className="w-full pl-9 pr-8 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-linkedin-blue"
                  />
                  {imageSearch && (
                    <button
                      type="button"
                      onClick={() => setImageSearch("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={!imageSearch.trim()}
                  className="px-4 py-2 bg-linkedin-blue text-white rounded-xl text-sm font-medium hover:bg-linkedin-blue-dark transition-colors disabled:opacity-40"
                >
                  Search
                </button>
                {activeSearch && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-xl transition-colors"
                  >
                    Clear
                  </button>
                )}
              </form>

              {activeSearch && (
                <p className="text-xs text-gray-400">
                  Results for <span className="font-medium text-gray-600">"{activeSearch}"</span>
                </p>
              )}

              {/* Grid */}
              {localImages.length > 0 ? (
                <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
                  {localImages.map((img) => (
                    <button
                      key={img.id}
                      onClick={() => setSelectedImageId(img.id)}
                      className={`relative aspect-square rounded-lg overflow-hidden border-2 transition-all group ${
                        selectedImageId === img.id
                          ? "border-linkedin-blue shadow-md scale-[1.03]"
                          : "border-transparent hover:border-gray-300"
                      }`}
                    >
                      <img
                        src={img.thumbnail_url}
                        alt={img.photographer ? `Photo by ${img.photographer}` : "Stock photo"}
                        className="w-full h-full object-cover"
                      />
                      {selectedImageId === img.id && (
                        <div className="absolute inset-0 bg-linkedin-blue/10 flex items-center justify-center">
                          <CheckCircle className="w-5 h-5 text-linkedin-blue drop-shadow" />
                        </div>
                      )}
                      {img.recommended && selectedImageId !== img.id && (
                        <div className="absolute top-1 left-1">
                          <span className="bg-linkedin-blue text-white text-[10px] px-1.5 py-0.5 rounded-full font-medium">
                            Best
                          </span>
                        </div>
                      )}
                      {img.photographer && (
                        <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-1 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className="text-white text-[9px] truncate block">{img.photographer}</span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  No images found.{" "}
                  {activeSearch ? "Try a different search term." : "Click Refresh to try again."}
                </div>
              )}

              <p className="text-xs text-gray-400">
                Photos by{" "}
                <a href="https://www.pexels.com" target="_blank" rel="noopener noreferrer" className="underline">
                  Pexels
                </a>
                {selectedImageId
                  ? " · 1 image selected"
                  : " · No image selected (post will be text-only)"}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Bottom actions ── */}
      {isReady && (
        <div className="flex items-center justify-between">
          {selectedImageId && imagesLoaded ? (
            <button
              onClick={() => setSelectedImageId("")}
              className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              Remove image selection
            </button>
          ) : (
            <span />
          )}
          <button
            onClick={handleContinue}
            disabled={saving}
            className="bg-linkedin-blue hover:bg-linkedin-blue-dark text-white font-semibold px-8 py-3 rounded-xl flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Preview Post
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export default function GeneratePageWrapper() {
  return (
    <Suspense>
      <GeneratePage />
    </Suspense>
  );
}
