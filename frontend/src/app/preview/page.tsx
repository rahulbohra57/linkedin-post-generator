"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Loader2,
  Copy,
  Check,
  ThumbsUp,
  MessageSquare,
  Share2,
  Download,
  RotateCcw,
} from "lucide-react";
import { getDraft, type Draft } from "@/lib/api";
import { usePostStore } from "@/store/postStore";

function PreviewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftId = Number(searchParams.get("draft_id"));

  const { selectedImageId, images } = usePostStore();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const selectedImage = images.find((i) => i.id === selectedImageId);

  useEffect(() => {
    if (!draftId) return;
    getDraft(draftId).then(setDraft);
  }, [draftId]);

  const handleCopy = () => {
    if (draft?.post_text) {
      navigator.clipboard.writeText(draft.post_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownloadImage = async () => {
    if (!selectedImage) return;
    setDownloading(true);
    try {
      const response = await fetch(selectedImage.url);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "linkedin-post-image.jpg";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
    } catch {
      // CORS fallback — open in new tab so user can save manually
      window.open(selectedImage.url, "_blank");
    } finally {
      setDownloading(false);
    }
  };

  if (!draft) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-linkedin-blue" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Post Preview</h2>
      <p className="text-gray-500 mb-8">
        Review your post, then copy the caption and download the image to post on LinkedIn.
      </p>

      {/* LinkedIn-style card preview */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden mb-6">
        {/* Card header */}
        <div className="p-4 flex items-start gap-3">
          <div className="w-12 h-12 rounded-full flex-shrink-0 overflow-hidden">
            <div className="w-full h-full bg-gradient-to-br from-linkedin-blue to-blue-400" />
          </div>
          <div>
            <div className="font-semibold text-gray-900 text-sm">Your Name</div>
            <div className="text-xs text-gray-500">Your LinkedIn Headline</div>
            <div className="text-xs text-gray-400">Just now · 🌐</div>
          </div>
        </div>

        {/* Post text */}
        <div className="px-4 pb-3">
          <PostTextPreview text={draft.post_text || ""} />
        </div>

        {/* Image */}
        {selectedImage && (
          <div className="aspect-video bg-gray-100 overflow-hidden">
            <img
              src={selectedImage.url}
              alt="Post image"
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* Engagement bar (decorative) */}
        <div className="px-4 py-3 border-t border-gray-100">
          <div className="flex items-center gap-1 text-xs text-gray-400 mb-2">
            <span>👍 🎉 💡</span>
            <span>47 reactions · 12 comments</span>
          </div>
          <div className="flex gap-1">
            {[
              { icon: ThumbsUp, label: "Like" },
              { icon: MessageSquare, label: "Comment" },
              { icon: Share2, label: "Repost" },
            ].map(({ icon: Icon, label }) => (
              <button
                key={label}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg hover:bg-gray-50 text-gray-500 text-sm font-medium flex-1 justify-center"
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Save your post</h3>

        {/* Copy caption */}
        <button
          onClick={handleCopy}
          className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors text-sm font-medium"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-green-500" />
              <span className="text-green-600">Caption copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              Copy Post Caption
            </>
          )}
        </button>

        {/* Download image */}
        {selectedImage ? (
          <button
            onClick={handleDownloadImage}
            disabled={downloading}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-linkedin-blue hover:bg-linkedin-blue-dark text-white font-semibold transition-colors disabled:opacity-60 text-sm"
          >
            {downloading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Downloading…
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Download Image
              </>
            )}
          </button>
        ) : (
          <div className="w-full flex items-center justify-center px-5 py-3 rounded-xl border border-dashed border-gray-200 text-gray-400 text-sm">
            No image selected — go back to choose one
          </div>
        )}

        {selectedImage?.photographer && (
          <p className="text-xs text-gray-400 text-center">
            Photo by {selectedImage.photographer} · via{" "}
            <a
              href="https://www.pexels.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-600"
            >
              Pexels
            </a>
          </p>
        )}
      </div>

      {/* Footer actions */}
      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={() => router.push(`/generate?draft_id=${draftId}`)}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Back to edit
        </button>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-linkedin-blue hover:underline font-medium"
        >
          Create another post →
        </button>
      </div>
    </div>
  );
}

function PostTextPreview({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const preview = text.slice(0, 210);
  const hasMore = text.length > 210;

  return (
    <p className="text-sm text-gray-800 whitespace-pre-line leading-relaxed">
      {expanded ? text : preview}
      {hasMore && !expanded && (
        <>
          {"... "}
          <button
            onClick={() => setExpanded(true)}
            className="text-gray-500 hover:text-gray-700 font-medium"
          >
            see more
          </button>
        </>
      )}
    </p>
  );
}

export default function PreviewPageWrapper() {
  return (
    <Suspense>
      <PreviewPage />
    </Suspense>
  );
}
