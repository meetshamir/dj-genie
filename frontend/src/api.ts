import { Song, Segment, SegmentWithSong, AnalysisResult, ExportStatus } from "./types";

const API_BASE = "/api";

// DJ Context type for AI DJ configuration
export interface DJContext {
  theme: string;
  mood: string;
  audience: string;
  special_notes?: string;
  custom_shoutouts?: string[];
}

export async function fetchSongs(): Promise<Song[]> {
  const response = await fetch(`${API_BASE}/songs`);
  if (!response.ok) throw new Error("Failed to fetch songs");
  return response.json();
}

export async function fetchSegments(): Promise<SegmentWithSong[]> {
  const response = await fetch(`${API_BASE}/segments`);
  if (!response.ok) throw new Error("Failed to fetch segments");
  return response.json();
}

export async function fetchSegmentsBySong(songId: number): Promise<Segment[]> {
  const response = await fetch(`${API_BASE}/songs/${songId}/segments`);
  if (!response.ok) throw new Error("Failed to fetch segments");
  return response.json();
}

export async function analyzeAllSongs(): Promise<{ results: AnalysisResult[] }> {
  const response = await fetch(`${API_BASE}/analyze-all`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to analyze songs");
  return response.json();
}

// DJ Context API functions
export async function saveDJContext(playlistId: string, context: DJContext): Promise<void> {
  const response = await fetch(`${API_BASE}/playlists/${playlistId}/dj-context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(context),
  });
  if (!response.ok) throw new Error("Failed to save DJ context");
}

export async function getDJContext(playlistId: string): Promise<DJContext | null> {
  const response = await fetch(`${API_BASE}/playlists/${playlistId}/dj-context`);
  if (!response.ok) return null;
  const data = await response.json();
  return data.dj_context || null;
}

export async function createPlaylist(
  name: string,
  segmentIds: string[],
  targetDuration: number = 2700
): Promise<{ playlist_id: string }> {
  const response = await fetch(`${API_BASE}/playlists`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      segment_ids: segmentIds,
      target_duration: targetDuration,
    }),
  });
  if (!response.ok) throw new Error("Failed to create playlist");
  return response.json();
}

export async function exportPlaylist(
  playlistId: string,
  options: {
    crossfadeDuration?: number;
    transitionType?: string;
    addTextOverlay?: boolean;
    videoQuality?: string;
    djEnabled?: boolean;
    djVoice?: string;
    djFrequency?: string;
  } = {}
): Promise<{ job_id: string; status: string; message: string }> {
  const params = new URLSearchParams();
  if (options.crossfadeDuration !== undefined) {
    params.append("crossfade_duration", options.crossfadeDuration.toString());
  }
  if (options.transitionType) {
    params.append("transition_type", options.transitionType);
  }
  if (options.addTextOverlay !== undefined) {
    params.append("add_text_overlay", options.addTextOverlay.toString());
  }
  if (options.videoQuality) {
    params.append("video_quality", options.videoQuality);
  }
  if (options.djEnabled !== undefined) {
    params.append("dj_enabled", options.djEnabled.toString());
  }
  if (options.djVoice) {
    params.append("dj_voice", options.djVoice);
  }
  if (options.djFrequency) {
    params.append("dj_frequency", options.djFrequency);
  }
  
  const response = await fetch(`${API_BASE}/playlists/${playlistId}/export?${params}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start export");
  return response.json();
}

export async function intelligentMix(
  playlistId: string,
  options: {
    strategy?: string;
    energyCurve?: string;
    maxSameLanguage?: number;
  } = {}
): Promise<{
  quality_score: number;
  notes: string[];
  new_order: Array<{
    position: number;
    segment_id: string;
    song_title: string;
    language: string;
    bpm: number | null;
    energy_score: number;
  }>;
}> {
  const params = new URLSearchParams();
  if (options.strategy) params.append("strategy", options.strategy);
  if (options.energyCurve) params.append("energy_curve", options.energyCurve);
  if (options.maxSameLanguage !== undefined) {
    params.append("max_same_language", options.maxSameLanguage.toString());
  }
  
  const response = await fetch(`${API_BASE}/playlists/${playlistId}/mix?${params}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to mix playlist");
  return response.json();
}

export async function getExportStatus(jobId: string): Promise<ExportStatus> {
  const response = await fetch(`${API_BASE}/export/jobs/${jobId}`);
  if (!response.ok) throw new Error("Failed to get export status");
  return response.json();
}

export function getExportDownloadUrl(jobId: string): string {
  return `${API_BASE}/export/jobs/${jobId}/download`;
}

export function getYouTubeEmbedUrl(videoId: string, startTime: number): string {
  return `https://www.youtube.com/embed/${videoId}?start=${Math.floor(startTime)}&autoplay=1&mute=0`;
}

export function getThumbnailUrl(videoId: string): string {
  return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function formatTimeRange(start: number, end: number): string {
  return `${formatDuration(start)} - ${formatDuration(end)}`;
}
