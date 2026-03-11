"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";

interface Candidate {
  start_time: number;
  end_time: number;
  title: string;
  reason: string;
  virality_score: number;
  hook: string;
  emojis: string[];
}

export default function CandidatesPage() {
  const params = useParams();
  const router = useRouter();
  const fileId = params.fileId as string;

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rendering, setRendering] = useState<Set<number>>(new Set());
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedCandidate, setEditedCandidate] = useState<Candidate | null>(null);
  const [platform, setPlatform] = useState<string>("tiktok");

  useEffect(() => {
    fetchCandidates();
  }, [fileId]);

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('cg_access_token') : null
      const response = await fetch(`${API_BASE}/clips/${fileId}/candidates`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        throw new Error("Failed to fetch candidates");
      }
      const data = await response.json();
      setCandidates(data.candidates);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const startEditing = (index: number) => {
    setEditingIndex(index);
    setEditedCandidate({ ...candidates[index] });
  };

  const cancelEditing = () => {
    setEditingIndex(null);
    setEditedCandidate(null);
  };

  const saveEditing = () => {
    if (editingIndex !== null && editedCandidate) {
      const updated = [...candidates];
      updated[editingIndex] = editedCandidate;
      setCandidates(updated);
      setEditingIndex(null);
      setEditedCandidate(null);
    }
  };

  const renderClip = async (index: number) => {
    try {
      setRendering((prev) => new Set(prev).add(index));
      
      const tokenR = typeof window !== 'undefined' ? localStorage.getItem('cg_access_token') : null
      const response = await fetch(`${API_BASE}/extract-clips/${fileId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenR ? { Authorization: `Bearer ${tokenR}` } : {}),
        },
        body: JSON.stringify({
          clip_indices: [index],
          enable_reframe: true,
          enable_subtitles: true,
          platform: platform,
        }),
      });

      if (!response.ok) {
        throw new Error("Rendering failed");
      }

      const result = await response.json();
      alert(`✓ Clip rendered successfully!\n${result.message}`);
    } catch (err) {
      alert(`✗ Rendering failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setRendering((prev) => {
        const updated = new Set(prev);
        updated.delete(index);
        return updated;
      });
    }
  };

  const renderAll = async () => {
    try {
      setRendering(new Set(candidates.map((_, i) => i)));
      
      const tokenA = typeof window !== 'undefined' ? localStorage.getItem('cg_access_token') : null
      const response = await fetch(`${API_BASE}/extract-clips/${fileId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenA ? { Authorization: `Bearer ${tokenA}` } : {}),
        },
        body: JSON.stringify({
          enable_reframe: true,
          enable_subtitles: true,
          platform: platform,
        }),
      });

      if (!response.ok) {
        throw new Error("Rendering failed");
      }

      const result = await response.json();
      alert(`✓ All clips rendered successfully!\n${result.message}`);
    } catch (err) {
      alert(`✗ Rendering failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setRendering(new Set());
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-black flex items-center justify-center">
        <div className="text-white text-2xl">Loading candidates...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-black flex items-center justify-center">
        <div className="text-red-400 text-xl">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-black p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push("/")}
            className="text-white/70 hover:text-white mb-4 flex items-center gap-2"
          >
            ← Back to Upload
          </button>
          <h1 className="text-4xl font-bold text-white mb-2">
            🎬 Clip Candidates Review
          </h1>
          <p className="text-white/70">
            Review AI-selected clips and choose which ones to render
          </p>
        </div>

        {/* Platform Selector */}
        <div className="mb-6 bg-white/10 backdrop-blur-sm rounded-lg p-4">
          <label className="text-white font-semibold mb-2 block">
            Target Platform:
          </label>
          <div className="flex gap-4">
            {["tiktok", "youtube", "instagram"].map((p) => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={`px-6 py-2 rounded-lg font-semibold transition-all ${
                  platform === p
                    ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white"
                    : "bg-white/20 text-white/70 hover:bg-white/30"
                }`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Render All Button */}
        <div className="mb-6">
          <button
            onClick={renderAll}
            disabled={rendering.size > 0}
            className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white font-bold py-4 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {rendering.size > 0 ? "⏳ Rendering..." : "🚀 Render All Clips"}
          </button>
        </div>

        {/* Candidates Grid */}
        <div className="space-y-6">
          {candidates.map((candidate, index) => (
            <div
              key={index}
              className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border-2 border-white/20 hover:border-purple-500/50 transition-all"
            >
              {editingIndex === index && editedCandidate ? (
                // Edit Mode
                <div className="space-y-4">
                  <input
                    type="text"
                    value={editedCandidate.title}
                    onChange={(e) =>
                      setEditedCandidate({ ...editedCandidate, title: e.target.value })
                    }
                    className="w-full bg-white/20 text-white px-4 py-2 rounded-lg border border-white/30 focus:border-purple-500 focus:outline-none"
                    placeholder="Title"
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-white/70 text-sm">Start Time (s)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={editedCandidate.start_time}
                        onChange={(e) =>
                          setEditedCandidate({
                            ...editedCandidate,
                            start_time: parseFloat(e.target.value),
                          })
                        }
                        className="w-full bg-white/20 text-white px-4 py-2 rounded-lg border border-white/30 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-white/70 text-sm">End Time (s)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={editedCandidate.end_time}
                        onChange={(e) =>
                          setEditedCandidate({
                            ...editedCandidate,
                            end_time: parseFloat(e.target.value),
                          })
                        }
                        className="w-full bg-white/20 text-white px-4 py-2 rounded-lg border border-white/30 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={saveEditing}
                      className="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-lg"
                    >
                      ✓ Save
                    </button>
                    <button
                      onClick={cancelEditing}
                      className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-2 rounded-lg"
                    >
                      ✗ Cancel
                    </button>
                  </div>
                </div>
              ) : (
                // View Mode
                <>
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-bold text-white">
                          {candidate.title}
                        </h3>
                        <div className="flex gap-1">
                          {candidate.emojis?.map((emoji, i) => (
                            <span key={i} className="text-2xl">
                              {emoji}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-white/70 text-sm mb-3">
                        <span>
                          ⏱️ {candidate.start_time.toFixed(1)}s - {candidate.end_time.toFixed(1)}s
                        </span>
                        <span>
                          📏 {(candidate.end_time - candidate.start_time).toFixed(1)}s duration
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-bold px-4 py-2 rounded-full">
                        🔥 {candidate.virality_score}/10
                      </div>
                      <div className="bg-purple-500/30 text-purple-200 px-3 py-1 rounded-full text-sm font-semibold">
                        {candidate.hook}
                      </div>
                    </div>
                  </div>

                  <div className="mb-4">
                    <h4 className="text-white/70 text-sm font-semibold mb-2">
                      Why This Will Go Viral:
                    </h4>
                    <p className="text-white/90">{candidate.reason}</p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => renderClip(index)}
                      disabled={rendering.has(index)}
                      className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {rendering.has(index) ? "⏳ Rendering..." : "🎬 Render This Clip"}
                    </button>
                    <button
                      onClick={() => startEditing(index)}
                      className="px-6 bg-white/20 hover:bg-white/30 text-white font-semibold rounded-lg transition-all"
                    >
                      ✏️ Edit
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
