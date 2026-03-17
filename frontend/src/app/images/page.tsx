"use client";
import { useEffect, useState, Suspense, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDropzone } from "react-dropzone";
import {
  Loader2,
  Upload,
  ChevronRight,
  RefreshCw,
  CheckCircle,
  Search,
  X,
} from "lucide-react";
import { getImages, uploadImage, type ImageResult } from "@/lib/api";
import { usePostStore } from "@/store/postStore";
import { getOrCreateSessionId } from "@/lib/utils";

function ImagesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftId = Number(searchParams.get("draft_id"));
  const sessionId = getOrCreateSessionId();

  const { setImages, setSelectedImageId, selectedImageId, images: cachedImages } =
    usePostStore();
  const [images, setLocalImages] = useState<ImageResult[]>(cachedImages);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Search state
  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const fetchImages = async (query?: string) => {
    setLoading(true);
    try {
      const result = await getImages(draftId, sessionId, query || undefined);
      setLocalImages(result.images);
      setImages(result.images);
      if (result.recommended_id) setSelectedImageId(result.recommended_id);
    } catch (e) {
      console.error("Failed to fetch images:", e);
    } finally {
      setLoading(false);
    }
  };

  // Always fetch fresh images when arriving at this page for a specific draft
  useEffect(() => {
    if (draftId) fetchImages();
  }, [draftId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchInput.trim();
    if (!q) return;
    setActiveSearch(q);
    fetchImages(q);
  };

  const handleClearSearch = () => {
    setActiveSearch(null);
    setSearchInput("");
    fetchImages();
  };

  const handleRefresh = () => {
    fetchImages(activeSearch || undefined);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "image/jpeg": [], "image/png": [], "image/webp": [] },
    maxSize: 5 * 1024 * 1024,
    onDrop: async (files) => {
      if (!files[0]) return;
      setUploading(true);
      try {
        const result = await uploadImage(files[0]);
        setLocalImages((prev) => [result, ...prev]);
        setImages([result, ...images]);
        setSelectedImageId(result.id);
      } finally {
        setUploading(false);
      }
    },
  });

  const handleContinue = () => {
    router.push(`/preview?draft_id=${draftId}`);
  };

  const pexelsImages = images.filter((i) => i.source === "stock");
  const uploadedImages = images.filter((i) => i.source === "uploaded");

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-2xl font-bold text-gray-900">Choose an Image</h2>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-linkedin-blue transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Suggestions
        </button>
      </div>
      <p className="text-gray-500 mb-5">
        Pick one of the suggested Pexels photos, search for something specific, or upload your own.
      </p>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="relative mb-6">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input
              ref={searchRef}
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search Pexels for images…"
              className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-linkedin-blue"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={!searchInput.trim() || loading}
            className="px-4 py-2.5 bg-linkedin-blue text-white rounded-xl text-sm font-semibold hover:bg-linkedin-blue-dark transition-colors disabled:opacity-40"
          >
            Search
          </button>
        </div>
        {activeSearch && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-gray-500">
              Showing results for <span className="font-semibold text-gray-700">"{activeSearch}"</span>
            </span>
            <button
              type="button"
              onClick={handleClearSearch}
              className="text-xs text-linkedin-blue hover:underline"
            >
              Clear search
            </button>
          </div>
        )}
      </form>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <Loader2 className="w-10 h-10 animate-spin mb-3 text-linkedin-blue" />
          <p className="text-sm">
            {activeSearch ? `Searching Pexels for "${activeSearch}"…` : "Finding the best stock photos for your post…"}
          </p>
        </div>
      )}

      {!loading && (
        <div className="space-y-6">
          {/* Pexels suggestions */}
          {pexelsImages.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                  {activeSearch ? "Search Results" : "Suggested Photos"} · Pexels
                </h3>
                <span className="text-xs text-gray-400">{pexelsImages.length} photos</span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                {pexelsImages.map((img) => (
                  <ImageCard
                    key={img.id}
                    image={img}
                    selected={selectedImageId === img.id}
                    onSelect={() => setSelectedImageId(img.id)}
                  />
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Photos provided by{" "}
                <a
                  href="https://www.pexels.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-gray-600"
                >
                  Pexels
                </a>
              </p>
            </div>
          )}

          {pexelsImages.length === 0 && !loading && (
            <div className="text-center py-10 text-gray-400 text-sm">
              No images found.{" "}
              {activeSearch ? "Try a different search term." : "Click Refresh Suggestions to try again."}
            </div>
          )}

          {/* Uploaded images */}
          {uploadedImages.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
                Your Uploads
              </h3>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                {uploadedImages.map((img) => (
                  <ImageCard
                    key={img.id}
                    image={img}
                    selected={selectedImageId === img.id}
                    onSelect={() => setSelectedImageId(img.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Upload dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? "border-linkedin-blue bg-linkedin-blue-light"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-linkedin-blue" />
            ) : (
              <>
                <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">
                  {isDragActive
                    ? "Drop your image here"
                    : "Drag & drop or click to upload your own image"}
                </p>
                <p className="text-xs text-gray-400 mt-1">JPG, PNG, WebP — max 5MB</p>
              </>
            )}
          </div>
        </div>
      )}

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={() => setSelectedImageId("")}
          className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          Skip image
        </button>
        <button
          onClick={handleContinue}
          className="bg-linkedin-blue hover:bg-linkedin-blue-dark text-white font-semibold px-8 py-3 rounded-xl flex items-center gap-2 transition-colors"
        >
          Preview & Publish
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function ImageCard({
  image,
  selected,
  onSelect,
}: {
  image: ImageResult;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`relative rounded-xl overflow-hidden aspect-square border-2 transition-all group ${
        selected
          ? "border-linkedin-blue shadow-lg scale-[1.02]"
          : "border-transparent hover:border-gray-300"
      }`}
    >
      <img
        src={image.thumbnail_url}
        alt={image.photographer ? `Photo by ${image.photographer}` : "Stock photo"}
        className="w-full h-full object-cover"
      />
      {selected && (
        <div className="absolute top-2 right-2">
          <CheckCircle className="w-5 h-5 text-white drop-shadow-md" />
        </div>
      )}
      {image.recommended && !selected && (
        <div className="absolute top-2 left-2">
          <span className="bg-linkedin-blue text-white text-xs px-2 py-0.5 rounded-full font-medium shadow">
            Suggested
          </span>
        </div>
      )}
      {/* Photographer credit on hover */}
      {image.photographer && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-white text-xs truncate block">
            {image.photographer}
          </span>
        </div>
      )}
    </button>
  );
}

export default function ImagesPageWrapper() {
  return (
    <Suspense>
      <ImagesPage />
    </Suspense>
  );
}
