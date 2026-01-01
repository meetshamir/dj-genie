export interface Song {
  id: string;
  youtube_id: string;
  title: string;
  artist: string | null;
  duration_seconds: number;
  language: string;
  thumbnail_url: string | null;
  view_count: number | null;
  bpm: number | null;
  analysis_status: "pending" | "analyzing" | "completed" | "failed";
  created_at: string;
}

export interface Segment {
  id: string;
  song_id: string;
  start_time: number;
  end_time: number;
  energy_score: number;
  peak_moment: number;
  segment_type: string;
  created_at: string;
  song?: Song;
}

export interface SegmentWithSong extends Segment {
  song: Song;
}

export interface Playlist {
  id: number;
  name: string;
  target_duration: number;
  created_at: string;
  updated_at: string;
}

export interface PlaylistItem {
  id: number;
  playlist_id: number;
  segment_id: number;
  position: number;
  crossfade_duration: number;
}

export interface AnalysisResult {
  song_id: number;
  status: string;
  segments_found: number;
  bpm: number | null;
  error?: string;
}

export interface ExportStatus {
  status: "pending" | "downloading" | "processing" | "encoding" | "complete" | "failed";
  progress: number;
  current_step: string;
  segment_index: number;
  total_segments: number;
  error?: string;
  result?: {
    success: boolean;
    output_path?: string;
    duration_seconds?: number;
    file_size_bytes?: number;
    error?: string;
  };
}
