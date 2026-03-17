"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, ChevronRight } from "lucide-react";
import { generatePost } from "@/lib/api";
import { usePostStore } from "@/store/postStore";
import { getOrCreateSessionId } from "@/lib/utils";

const TONES = [
  { value: "professional", label: "Professional" },
  { value: "conversational", label: "Conversational" },
  { value: "thought_leader", label: "Thought Leader" },
  { value: "educational", label: "Educational" },
  { value: "inspirational", label: "Inspirational" },
] as const;

const AUDIENCES = ["Developers", "Founders", "Marketers", "Executives", "Students", "Data Scientists"];
const LENGTHS = [
  { value: "short", label: "Short", desc: "~100 words" },
  { value: "medium", label: "Medium", desc: "~200 words" },
  { value: "long", label: "Long", desc: "~300 words" },
] as const;

export default function HomePage() {
  const router = useRouter();
  const { setSessionId, setDraftId, reset } = usePostStore();

  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState<typeof TONES[number]["value"]>("professional");
  const [audience, setAudience] = useState("professionals");
  const [length, setLength] = useState<"short" | "medium" | "long">("medium");
  const [loading, setLoading] = useState(false);
  const [warming, setWarming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const sid = getOrCreateSessionId();
    setSessionId(sid);
    reset();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setWarming(true);
    setError("");

    // Wake up the backend if it's sleeping (Render free tier spins down after inactivity)
    try {
      await fetch("/api/health-proxy");
    } catch {}
    setWarming(false);

    try {
      const sessionId = getOrCreateSessionId();
      const res = await generatePost({
        topic,
        tone,
        target_audience: audience,
        post_length: length,
        session_id: sessionId,
      });
      setDraftId(res.draft_id);
      router.push(`/generate?draft_id=${res.draft_id}`);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to start generation. Please try again.");
      setLoading(false);
      setWarming(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-3xl font-bold text-gray-900 mb-3">
          Create Your LinkedIn Post
        </h2>
        <p className="text-gray-500 text-lg">
          8 AI agents research, write, edit, and optimize your post — ready to copy and post.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
        {/* Topic */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            What do you want to post about?
          </label>
          <textarea
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent resize-none"
            rows={3}
            placeholder="e.g., How AI agents are changing software development in 2025"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            maxLength={512}
            required
          />
          <p className="text-xs text-gray-400 mt-1 text-right">{topic.length}/512</p>
        </div>

        {/* Tone */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Tone</label>
          <div className="flex flex-wrap gap-2">
            {TONES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setTone(t.value)}
                className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${
                  tone === t.value
                    ? "bg-linkedin-blue text-white border-linkedin-blue"
                    : "bg-white text-gray-600 border-gray-200 hover:border-linkedin-blue hover:text-linkedin-blue"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Audience */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Target Audience</label>
          <div className="flex flex-wrap gap-2 mb-2">
            {AUDIENCES.map((a) => (
              <button
                key={a}
                type="button"
                onClick={() => setAudience(a)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  audience === a
                    ? "bg-blue-50 text-linkedin-blue border-linkedin-blue"
                    : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
          <input
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-linkedin-blue"
            placeholder="Or type a custom audience..."
            value={AUDIENCES.includes(audience as any) ? "" : audience}
            onChange={(e) => setAudience(e.target.value || "professionals")}
          />
        </div>

        {/* Length */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Post Length</label>
          <div className="grid grid-cols-3 gap-3">
            {LENGTHS.map((l) => (
              <button
                key={l.value}
                type="button"
                onClick={() => setLength(l.value)}
                className={`py-3 rounded-xl border text-sm font-medium transition-all ${
                  length === l.value
                    ? "bg-linkedin-blue text-white border-linkedin-blue"
                    : "bg-white text-gray-600 border-gray-200 hover:border-linkedin-blue"
                }`}
              >
                <div className="font-semibold">{l.label}</div>
                <div className={`text-xs mt-0.5 ${length === l.value ? "text-blue-100" : "text-gray-400"}`}>
                  {l.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
        )}

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="w-full bg-linkedin-blue hover:bg-linkedin-blue-dark disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl flex items-center justify-center gap-2 transition-colors"
        >
          {loading ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              {warming ? "Waking up backend…" : "Starting generation..."}
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate Post
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      {/* How it works */}
      <div className="mt-8 grid grid-cols-4 gap-4 text-center">
        {[
          { step: "1", title: "Research", desc: "AI finds latest facts & trends" },
          { step: "2", title: "Write & Edit", desc: "Multiple agents refine the post" },
          { step: "3", title: "Pick Image", desc: "Choose from Pexels stock photos" },
          { step: "4", title: "Export", desc: "Copy caption & download image" },
        ].map((item) => (
          <div key={item.step} className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="w-7 h-7 bg-linkedin-blue-light text-linkedin-blue rounded-full flex items-center justify-center text-xs font-bold mx-auto mb-2">
              {item.step}
            </div>
            <div className="text-sm font-semibold text-gray-800">{item.title}</div>
            <div className="text-xs text-gray-400 mt-0.5">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
