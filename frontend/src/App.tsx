import { useState, useEffect, useCallback } from "react";
import { SegmentWithSong, ExportStatus } from "./types";
import {
  fetchSegments,
  getThumbnailUrl,
  getYouTubeEmbedUrl,
  formatTimeRange,
  formatDuration,
  createPlaylist,
  exportPlaylist,
  getExportStatus,
  getExportDownloadUrl,
  intelligentMix,
  DJContext,
  saveDJContext,
} from "./api";
import DJContextChat from "./components/DJContextChat";

const LANGUAGES = [
  "all",
  "english",
  "hindi",
  "malayalam",
  "tamil",
  "turkish",
  "uzbek",
  "arabic",
];

const TRANSITIONS = [
  { value: "random", label: "Random Mix" },
  { value: "fade", label: "Fade" },
  { value: "fadeblack", label: "Fade Black" },
  { value: "fadewhite", label: "Fade White" },
  { value: "slideleft", label: "Slide Left" },
  { value: "slideright", label: "Slide Right" },
  { value: "circleopen", label: "Circle Open" },
  { value: "circleclose", label: "Circle Close" },
  { value: "dissolve", label: "Dissolve" },
  { value: "pixelize", label: "Pixelize" },
  { value: "wipeleft", label: "Wipe Left" },
  { value: "wiperight", label: "Wipe Right" },
];

const QUALITY_OPTIONS = [
  { value: "480p", label: "480p (Fast)" },
  { value: "720p", label: "720p (Balanced)" },
  { value: "1080p", label: "1080p (HD)" },
];

const MIX_STRATEGIES = [
  { value: "balanced", label: "Balanced" },
  { value: "bpm_smooth", label: "BPM Smooth" },
  { value: "energy_curve", label: "Energy Flow" },
  { value: "language_variety", label: "Language Variety" },
];

const DJ_VOICES = [
  { value: "energetic_male", label: "🎤 Energetic Male" },
  { value: "energetic_female", label: "🎙️ Energetic Female" },
  { value: "deep_male", label: "🔊 Deep Male" },
  { value: "party_female", label: "🎉 Party Female" },
  { value: "hype_male", label: "🔥 Hype Master" },
];

const DJ_FREQUENCY = [
  { value: "minimal", label: "Minimal (Intro/Outro only)" },
  { value: "moderate", label: "Moderate (Every 3-4 songs)" },
  { value: "frequent", label: "Frequent (Every 2 songs)" },
  { value: "maximum", label: "Maximum (Every song)" },
];

interface ExportSettings {
  crossfadeDuration: number;
  transitionType: string;
  videoQuality: string;
  addTextOverlay: boolean;
  djEnabled: boolean;
  djVoice: string;
  djFrequency: string;
}

function App() {
  const [segments, setSegments] = useState<SegmentWithSong[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportStatus | null>(null);
  const [lastPlaylistId, setLastPlaylistId] = useState<string | null>(null);
  const [lastExportJobId, setLastExportJobId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [mixing, setMixing] = useState(false);
  const [exportSettings, setExportSettings] = useState<ExportSettings>({
    crossfadeDuration: 1.5,
    transitionType: "random",
    videoQuality: "720p",
    addTextOverlay: true,
    djEnabled: false,
    djVoice: "energetic_male",
    djFrequency: "moderate",
  });
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  useEffect(() => {
    loadSegments();
  }, []);

  const loadSegments = async () => {
    try {
      setLoading(true);
      const data = await fetchSegments();
      data.sort((a, b) => b.energy_score - a.energy_score);
      setSegments(data);
    } catch (error) {
      showToast("Failed to load segments", "error");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const filteredSegments =
    filter === "all"
      ? segments
      : segments.filter(
          (s) => s.song?.language.toLowerCase() === filter.toLowerCase()
        );

  const toggleSegment = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const removeFromPlaylist = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const clearPlaylist = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const selectAllFiltered = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      filteredSegments.forEach((s) => next.add(s.id));
      return next;
    });
  };

  const selectedSegments = segments.filter((s) => selectedIds.has(s.id));
  const totalDuration = selectedSegments.reduce(
    (sum, s) => sum + (s.end_time - s.start_time),
    0
  );

  const allFilteredSelected = filteredSegments.length > 0 && 
    filteredSegments.every((s) => selectedIds.has(s.id));

  const handleCreatePlaylist = async () => {
    if (selectedSegments.length === 0) {
      showToast("Select segments to create a playlist", "error");
      return;
    }

    setCreating(true);
    try {
      const result = await createPlaylist(
        "DJ Mix " + new Date().toLocaleDateString(),
        selectedSegments.map((s) => s.id)
      );
      setLastPlaylistId(result.playlist_id);
      showToast("Playlist created! Ready to export.", "success");
    } catch (error) {
      showToast("Failed to create playlist", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleExportVideo = async () => {
    if (!lastPlaylistId) {
      showToast("Create a playlist first", "error");
      return;
    }

    setExporting(true);
    setExportProgress(null);
    
    try {
      const { job_id } = await exportPlaylist(lastPlaylistId, {
        crossfadeDuration: exportSettings.crossfadeDuration,
        transitionType: exportSettings.transitionType,
        addTextOverlay: exportSettings.addTextOverlay,
        videoQuality: exportSettings.videoQuality,
        djEnabled: exportSettings.djEnabled,
        djVoice: exportSettings.djVoice,
        djFrequency: exportSettings.djFrequency,
      });
      setLastExportJobId(job_id);
      showToast("Export started! This may take several minutes...", "success");
      
      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const status = await getExportStatus(job_id);
          setExportProgress(status);
          
          if (status.status === "complete") {
            clearInterval(pollInterval);
            setExporting(false);
            showToast("Export complete! Click Download to get your video.", "success");
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            setExporting(false);
            showToast("Export failed: " + (status.error || "Unknown error"), "error");
          }
        } catch {
          clearInterval(pollInterval);
          setExporting(false);
          showToast("Lost connection to export job", "error");
        }
      }, 2000);
    } catch (error) {
      setExporting(false);
      showToast("Failed to start export", "error");
    }
  };

  const handleIntelligentMix = async () => {
    if (!lastPlaylistId) {
      showToast("Create a playlist first", "error");
      return;
    }

    setMixing(true);
    try {
      const result = await intelligentMix(lastPlaylistId, {
        strategy: "balanced",
        energyCurve: "peak_middle",
        maxSameLanguage: 2,
      });
      showToast(`Playlist optimized! Quality score: ${result.quality_score}%`, "success");
    } catch (error) {
      showToast("Failed to optimize playlist", "error");
    } finally {
      setMixing(false);
    }
  };

  const handleDownload = () => {
    if (exportProgress?.status === "complete" && lastExportJobId) {
      window.open(getExportDownloadUrl(lastExportJobId), "_blank");
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Video DJ Playlist</h1>
        <a href="#/ai-dj" className="btn btn-primary" style={{ marginLeft: "auto", textDecoration: "none" }}>
          ✨ AI DJ Studio
        </a>
        <a href="#/ai-dj" className="btn btn-primary" style={{ marginLeft: "auto", textDecoration: "none" }}>
          ✨ AI DJ Studio
        </a>
        <a href="#/ai-dj" className="btn btn-primary" style={{ marginLeft: "auto", textDecoration: "none" }}>
          ✨ AI DJ Studio
        </a>
        <div className="header-stats">
          <span>
            <strong>{segments.length}</strong> segments
          </span>
          <span>
            <strong>{new Set(segments.map((s) => s.song_id)).size}</strong> songs
          </span>
          <span>
            <strong>{LANGUAGES.length - 1}</strong> languages
          </span>
        </div>
      </header>

      <main className="main-content">
        <section className="segment-panel">
          <div className="filter-bar">
            {LANGUAGES.map((lang) => (
              <button
                key={lang}
                className={"filter-btn " + (filter === lang ? "active" : "")}
                onClick={() => setFilter(lang)}
              >
                {lang === "all" ? "All" : lang.charAt(0).toUpperCase() + lang.slice(1)}
              </button>
            ))}
            <button
              className={"filter-btn select-all " + (allFilteredSelected ? "active" : "")}
              onClick={selectAllFiltered}
              style={{ marginLeft: "auto" }}
            >
              Select All {filter !== "all" ? filter.charAt(0).toUpperCase() + filter.slice(1) : ""}
            </button>
          </div>

          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
            </div>
          ) : (
            <div className="segment-grid">
              {filteredSegments.map((segment) => (
                <SegmentCard
                  key={segment.id}
                  segment={segment}
                  isSelected={selectedIds.has(segment.id)}
                  isHovered={hoveredId === segment.id}
                  onClick={() => toggleSegment(segment.id)}
                  onMouseEnter={() => setHoveredId(segment.id)}
                  onMouseLeave={() => setHoveredId(null)}
                />
              ))}
            </div>
          )}
        </section>

        <aside className="playlist-panel">
          <div className="playlist-header">
            <h2>Your Playlist</h2>
            <p className="playlist-duration">
              Duration: <strong>{formatDuration(totalDuration)}</strong> / 45:00
            </p>
          </div>

          <div className="playlist-items">
            {selectedSegments.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">&#127926;</div>
                <p>Click segments to add them to your playlist</p>
              </div>
            ) : (
              selectedSegments.map((segment, index) => (
                <div key={segment.id} className="playlist-item">
                  <span className="playlist-item-number">{index + 1}</span>
                  <div className="playlist-item-thumb">
                    <img
                      src={getThumbnailUrl(segment.song?.youtube_id || "")}
                      alt=""
                    />
                  </div>
                  <div className="playlist-item-info">
                    <div className="playlist-item-title">
                      {segment.song?.title || "Unknown"}
                    </div>
                    <div className="playlist-item-time">
                      {formatTimeRange(segment.start_time, segment.end_time)}
                    </div>
                  </div>
                  <button
                    className="playlist-item-remove"
                    onClick={() => removeFromPlaylist(segment.id)}
                  >
                    x
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="playlist-actions">
            {!lastPlaylistId ? (
              <button
                className="btn btn-primary"
                onClick={handleCreatePlaylist}
                disabled={selectedSegments.length === 0 || creating}
              >
                {creating ? "Creating..." : `Create Playlist (${selectedSegments.length} segments)`}
              </button>
            ) : (
              <>
                {/* Export Settings Panel */}
                <div className="export-settings">
                  <button 
                    className="settings-toggle"
                    onClick={() => setShowSettings(!showSettings)}
                  >
                    ⚙️ Export Settings {showSettings ? "▲" : "▼"}
                  </button>
                  
                  {showSettings && (
                    <div className="settings-panel">
                      <div className="setting-row">
                        <label>Transition:</label>
                        <select 
                          value={exportSettings.transitionType}
                          onChange={(e) => setExportSettings(s => ({...s, transitionType: e.target.value}))}
                        >
                          {TRANSITIONS.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>
                      </div>
                      
                      <div className="setting-row">
                        <label>Crossfade: {exportSettings.crossfadeDuration}s</label>
                        <input 
                          type="range"
                          min="0.5"
                          max="3"
                          step="0.5"
                          value={exportSettings.crossfadeDuration}
                          onChange={(e) => setExportSettings(s => ({...s, crossfadeDuration: parseFloat(e.target.value)}))}
                        />
                      </div>
                      
                      <div className="setting-row">
                        <label>Quality:</label>
                        <select 
                          value={exportSettings.videoQuality}
                          onChange={(e) => setExportSettings(s => ({...s, videoQuality: e.target.value}))}
                        >
                          {QUALITY_OPTIONS.map(q => (
                            <option key={q.value} value={q.value}>{q.label}</option>
                          ))}
                        </select>
                      </div>
                      
                      <div className="setting-row checkbox">
                        <label>
                          <input 
                            type="checkbox"
                            checked={exportSettings.addTextOverlay}
                            onChange={(e) => setExportSettings(s => ({...s, addTextOverlay: e.target.checked}))}
                          />
                          Show song title & language
                        </label>
                      </div>
                      
                      {/* AI DJ Settings */}
                      <div className="setting-section">
                        <div className="setting-row checkbox">
                          <label>
                            <input 
                              type="checkbox"
                              checked={exportSettings.djEnabled}
                              onChange={(e) => setExportSettings(s => ({...s, djEnabled: e.target.checked}))}
                            />
                            🎙️ Enable AI DJ Voice
                          </label>
                        </div>
                        
                        {exportSettings.djEnabled && (
                          <>
                            <div className="setting-row">
                              <label>DJ Voice:</label>
                              <select 
                                value={exportSettings.djVoice}
                                onChange={(e) => setExportSettings(s => ({...s, djVoice: e.target.value}))}
                              >
                                {DJ_VOICES.map(v => (
                                  <option key={v.value} value={v.value}>{v.label}</option>
                                ))}
                              </select>
                            </div>
                            
                            <div className="setting-row">
                              <label>Comment Frequency:</label>
                              <select 
                                value={exportSettings.djFrequency}
                                onChange={(e) => setExportSettings(s => ({...s, djFrequency: e.target.value}))}
                              >
                                {DJ_FREQUENCY.map(f => (
                                  <option key={f.value} value={f.value}>{f.label}</option>
                                ))}
                              </select>
                            </div>
                            
                            {/* DJ Context Chatbox */}
                            {lastPlaylistId && (
                              <div className="mt-4">
                                <DJContextChat
                                  playlistId={lastPlaylistId}
                                  onContextSaved={(ctx) => {
                                    console.log("DJ context saved:", ctx);
                                  }}
                                />
                              </div>
                            )}
                            
                            <div className="dj-preview">
                              <small>🎤 AI DJ uses GPT-4 to generate creative, themed commentary with your party vibe!</small>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <button
                  className="btn btn-secondary"
                  onClick={handleIntelligentMix}
                  disabled={mixing || exporting}
                >
                  {mixing ? "Optimizing..." : "🎛️ Smart Mix"}
                </button>
                
                <button
                  className="btn btn-primary"
                  onClick={handleExportVideo}
                  disabled={exporting}
                >
                  {exporting ? "Exporting..." : "🎬 Export Video"}
                </button>
                
                {exportProgress && exportProgress.status !== "complete" && (
                  <div className="export-progress">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ width: `${exportProgress.progress}%` }}
                      />
                    </div>
                    <span className="progress-text">{exportProgress.current_step}</span>
                  </div>
                )}
                {exportProgress?.status === "complete" && (
                  <button className="btn btn-success" onClick={handleDownload}>
                    ⬇️ Download Video
                  </button>
                )}
                <button 
                  className="btn btn-secondary" 
                  onClick={() => {
                    setLastPlaylistId(null);
                    setExportProgress(null);
                    setShowSettings(false);
                  }}
                >
                  New Playlist
                </button>
              </>
            )}
            {selectedSegments.length > 0 && !lastPlaylistId && (
              <button className="btn btn-secondary" onClick={clearPlaylist}>
                Clear All
              </button>
            )}
          </div>
        </aside>
      </main>

      {toast && <div className={"toast " + toast.type}>{toast.message}</div>}
    </div>
  );
}

interface SegmentCardProps {
  segment: SegmentWithSong;
  isSelected: boolean;
  isHovered: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

function SegmentCard({
  segment,
  isSelected,
  isHovered,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: SegmentCardProps) {
  const duration = segment.end_time - segment.start_time;
  const youtubeId = segment.song?.youtube_id || "";

  return (
    <div
      className={"segment-card " + (isSelected ? "selected" : "")}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="segment-thumbnail">
        {isHovered ? (
          <iframe
            src={getYouTubeEmbedUrl(youtubeId, segment.start_time)}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope"
            allowFullScreen
          />
        ) : (
          <img src={getThumbnailUrl(youtubeId)} alt={segment.song?.title} />
        )}
        <div className="segment-overlay">
          <span className="segment-time">
            {formatTimeRange(segment.start_time, segment.end_time)}
          </span>
          <span className="energy-badge">
            {(segment.energy_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="segment-info">
        <div className="segment-title">{segment.song?.title || "Unknown"}</div>
        <div className="segment-meta">
          <span className="language-tag">{segment.song?.language}</span>
          <span>{formatDuration(duration)}</span>
          {segment.song?.bpm && <span>{segment.song.bpm} BPM</span>}
        </div>
      </div>
    </div>
  );
}

export default App;
