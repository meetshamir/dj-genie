import { useState, useRef, useEffect, useCallback } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Song {
  title: string;
  artist: string;
  why?: string;
  youtube_id?: string;
}

interface PlaylistPlan {
  ready?: boolean;
  theme?: string;
  mood?: string[];
  languages?: string[];
  duration_minutes?: number;
  songs?: Song[];
  commentary_samples?: string[];
  shoutouts?: string[];
  party_people?: string[];
  cultural_phrases?: Record<string, string[]>;
}

interface TimelineEntry {
  time: string;
  type: 'song' | 'dj_comment';
  title?: string;
  artist?: string;
  language?: string;
  text?: string;
  comment_type?: string;
}

interface ExportProgress {
  status: string;
  progress: number;
  current_step: string;
  eta_seconds?: number;
  hls_segments_ready?: number;
  hls_playlist_path?: string;
  output_path?: string;
  error?: string;
  result?: {
    output_path?: string;
    song_timeline?: Array<{
      start_time: number;
      title: string;
      artist: string;
      language: string;
    }>;
    dj_timeline?: Array<{
      start_time: number;
      text: string;
      type: string;
    }>;
  };
}

export default function AIPlaylistPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [plan, setPlan] = useState<PlaylistPlan | null>(null);
  const [editingShoutouts, setEditingShoutouts] = useState(false);
  const [shoutouts, setShoutouts] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [mixTimeline, setMixTimeline] = useState<TimelineEntry[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket for export progress
  useEffect(() => {
    if (!jobId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//localhost:9876/ws/export/${jobId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setExportProgress(data);
      
      if (data.status === 'complete' && data.result) {
        // Build combined timeline from songs and DJ comments
        const timeline: TimelineEntry[] = [];
        
        // Add songs to timeline
        if (data.result.song_timeline) {
          for (const song of data.result.song_timeline) {
            const mins = Math.floor(song.start_time / 60);
            const secs = Math.floor(song.start_time % 60);
            timeline.push({
              time: `${mins}:${secs.toString().padStart(2, '0')}`,
              type: 'song',
              title: song.title,
              artist: song.artist,
              language: song.language
            });
          }
        }
        
        // Add DJ comments to timeline
        if (data.result.dj_timeline) {
          for (const comment of data.result.dj_timeline) {
            const mins = Math.floor(comment.start_time / 60);
            const secs = Math.floor(comment.start_time % 60);
            timeline.push({
              time: `${mins}:${secs.toString().padStart(2, '0')}`,
              type: 'dj_comment',
              text: comment.text,
              comment_type: comment.type
            });
          }
        }
        
        // Sort by time
        timeline.sort((a, b) => {
          const [aMins, aSecs] = a.time.split(':').map(Number);
          const [bMins, bSecs] = b.time.split(':').map(Number);
          return (aMins * 60 + aSecs) - (bMins * 60 + bSecs);
        });
        
        setMixTimeline(timeline);
        
        // Add timeline message to chat
        if (timeline.length > 0) {
          let timelineText = '\n\n📋 **Mix Timeline:**\n';
          for (const entry of timeline) {
            if (entry.type === 'song') {
              timelineText += `\n⏱️ ${entry.time} - 🎵 **${entry.title}** by ${entry.artist}`;
            } else {
              const emoji = entry.comment_type === 'intro' ? '🎬' :
                           entry.comment_type === 'outro' ? '🎤' :
                           entry.comment_type === 'shoutout' ? '🙌' :
                           entry.comment_type === 'cultural' ? '🌍' : '🗣️';
              timelineText += `\n⏱️ ${entry.time} - ${emoji} "${entry.text}"`;
            }
          }
          setMessages(prev => [...prev, { role: 'assistant', content: '✅ **Your mix is ready!**' + timelineText + '\n\n⬇️ Download your mix from the panel on the right!' }]);
        }
        
        ws.close();
      } else if (data.status === 'failed') {
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [jobId]);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: message }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/ai-chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'content') {
                  assistantMessage += data.content;
                  setMessages(prev => {
                    const newMessages = [...prev];
                    const lastIdx = newMessages.length - 1;
                    if (lastIdx >= 0 && newMessages[lastIdx].role === 'assistant') {
                      newMessages[lastIdx] = { role: 'assistant', content: assistantMessage };
                    } else {
                      newMessages.push({ role: 'assistant', content: assistantMessage });
                    }
                    return newMessages;
                  });
                } else if (data.type === 'plan') {
                  setPlan(data.plan);
                  setShoutouts(data.plan.shoutouts || []);
                } else if (data.type === 'done') {
                  setSessionId(data.session_id);
                } else if (data.type === 'error') {
                  console.error('Chat error:', data.error);
                }
              } catch (e) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, something went wrong. Please try again! 😅' 
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  const handleApprove = async () => {
    if (!sessionId || !plan) return;

    try {
      const response = await fetch('/api/ai-chat/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          modifications: { shoutouts }
        })
      });

      const data = await response.json();
      if (data.success) {
        setJobId(data.job_id);
      }
    } catch (error) {
      console.error('Approve error:', error);
    }
  };

  const handleYolo = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/ai-chat/yolo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'YOLO' })
      });

      const data = await response.json();
      if (data.success) {
        setSessionId(data.session_id);
        setJobId(data.job_id);
        setMessages([{ 
          role: 'assistant', 
          content: `🎲 ${data.message}` 
        }]);
      }
    } catch (error) {
      console.error('YOLO error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (jobId) {
      // Use backend URL directly since window.open doesn't go through Vite proxy
      const backendUrl = import.meta.env.DEV ? 'http://localhost:9876' : '';
      window.open(`${backendUrl}/api/export/jobs/${jobId}/download`, '_blank');
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#111827', color: 'white' }}>
      {/* Left Panel - Chat */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #374151' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid #374151' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🧞‍♂️ DJ Genie
          </h1>
          <p style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>Describe Your Vibe. We'll Drop the Beat.</p>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#6B7280', marginTop: '2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎵</div>
              <p>Start by telling me about your event!</p>
              <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Or hit YOLO for a surprise mix 🎲</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} style={{ 
              display: 'flex', 
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: '1rem'
            }}>
              <div style={{ 
                maxWidth: '80%', 
                borderRadius: '0.5rem', 
                padding: '0.75rem',
                backgroundColor: msg.role === 'user' ? '#7C3AED' : '#374151',
                whiteSpace: 'pre-wrap'
              }}>
                {msg.content}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{ backgroundColor: '#374151', borderRadius: '0.5rem', padding: '0.75rem' }}>
                <span>Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '1rem', borderTop: '1px solid #374151' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleYolo}
              disabled={isLoading || !!jobId}
              style={{ 
                padding: '0.5rem 1rem', 
                background: 'linear-gradient(to right, #EC4899, #F97316)',
                borderRadius: '0.5rem',
                fontWeight: 'bold',
                border: 'none',
                color: 'white',
                cursor: isLoading || jobId ? 'not-allowed' : 'pointer',
                opacity: isLoading || jobId ? 0.5 : 1
              }}
            >
              🎲 YOLO
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage(input)}
              placeholder="Describe your perfect party mix..."
              disabled={isLoading || !!jobId}
              style={{ 
                flex: 1, 
                backgroundColor: '#1F2937', 
                borderRadius: '0.5rem', 
                padding: '0.5rem 1rem',
                border: '1px solid #374151',
                color: 'white',
                outline: 'none'
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading || !!jobId}
              style={{ 
                padding: '0.5rem 1rem', 
                backgroundColor: '#7C3AED',
                borderRadius: '0.5rem',
                border: 'none',
                color: 'white',
                cursor: !input.trim() || isLoading || jobId ? 'not-allowed' : 'pointer',
                opacity: !input.trim() || isLoading || jobId ? 0.5 : 1
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - Plan Preview / Export Progress */}
      <div style={{ width: '24rem', display: 'flex', flexDirection: 'column', backgroundColor: '#1F2937' }}>
        {jobId && exportProgress ? (
          // Export Progress View
          <div style={{ flex: 1, padding: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem' }}>Creating Your Mix</h2>
            
            {/* Progress Bar */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                <span>{exportProgress.current_step || 'Processing...'}</span>
                <span>{Math.round(exportProgress.progress || 0)}%</span>
              </div>
              <div style={{ height: '0.75rem', backgroundColor: '#374151', borderRadius: '9999px', overflow: 'hidden' }}>
                <div 
                  style={{ 
                    height: '100%', 
                    background: 'linear-gradient(to right, #7C3AED, #EC4899)',
                    transition: 'width 0.3s',
                    width: `${exportProgress.progress || 0}%`
                  }}
                />
              </div>
            </div>

            {/* Status */}
            {exportProgress.status === 'complete' && (
              <div style={{ 
                backgroundColor: 'rgba(16, 185, 129, 0.2)', 
                border: '1px solid #10B981', 
                borderRadius: '0.5rem', 
                padding: '1rem', 
                textAlign: 'center' 
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✅</div>
                <p style={{ fontWeight: 'bold' }}>Mix Complete!</p>
                <button 
                  onClick={handleDownload}
                  style={{ 
                    marginTop: '0.5rem',
                    padding: '0.5rem 1rem',
                    backgroundColor: '#10B981',
                    borderRadius: '0.5rem',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  ⬇️ Download
                </button>
              </div>
            )}

            {exportProgress.status === 'failed' && (
              <div style={{ 
                backgroundColor: 'rgba(239, 68, 68, 0.2)', 
                border: '1px solid #EF4444', 
                borderRadius: '0.5rem', 
                padding: '1rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>❌</div>
                <p>{exportProgress.error || 'Export failed'}</p>
              </div>
            )}
          </div>
        ) : plan ? (
          // Plan Preview View
          <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>{plan.theme || 'Your Mix'}</h2>
            
            {/* Mood Tags */}
            {plan.mood && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                {plan.mood.map((m, i) => (
                  <span key={i} style={{ 
                    padding: '0.25rem 0.5rem', 
                    backgroundColor: 'rgba(124, 58, 237, 0.5)', 
                    borderRadius: '9999px', 
                    fontSize: '0.875rem' 
                  }}>
                    {m}
                  </span>
                ))}
              </div>
            )}

            {/* Songs */}
            <div style={{ marginBottom: '1rem' }}>
              <h3 style={{ fontWeight: '600', color: '#D1D5DB', marginBottom: '0.5rem' }}>Songs</h3>
              {plan.songs?.map((song, idx) => (
                <div key={idx} style={{ backgroundColor: '#374151', borderRadius: '0.5rem', padding: '0.75rem', marginBottom: '0.5rem' }}>
                  <p style={{ fontWeight: '500' }}>{song.title}</p>
                  <p style={{ fontSize: '0.875rem', color: '#9CA3AF' }}>{song.artist}</p>
                  {song.why && <p style={{ fontSize: '0.75rem', color: '#A78BFA', marginTop: '0.25rem' }}>{song.why}</p>}
                </div>
              ))}
            </div>

            {/* Shoutouts */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <h3 style={{ fontWeight: '600', color: '#D1D5DB' }}>Shoutouts</h3>
                <button 
                  onClick={() => setEditingShoutouts(!editingShoutouts)}
                  style={{ color: '#A78BFA', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  ✏️
                </button>
              </div>
              {editingShoutouts ? (
                <div>
                  {shoutouts.map((s, i) => (
                    <input
                      key={i}
                      value={s}
                      onChange={(e) => {
                        const newShoutouts = [...shoutouts];
                        newShoutouts[i] = e.target.value;
                        setShoutouts(newShoutouts);
                      }}
                      style={{ 
                        width: '100%', 
                        backgroundColor: '#374151', 
                        borderRadius: '0.25rem', 
                        padding: '0.25rem 0.5rem', 
                        fontSize: '0.875rem',
                        marginBottom: '0.25rem',
                        border: '1px solid #4B5563',
                        color: 'white'
                      }}
                    />
                  ))}
                  <button
                    onClick={() => setShoutouts([...shoutouts, ''])}
                    style={{ fontSize: '0.875rem', color: '#A78BFA', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    + Add shoutout
                  </button>
                </div>
              ) : (
                <div>
                  {shoutouts.map((s, i) => (
                    <p key={i} style={{ fontSize: '0.875rem', color: '#9CA3AF' }}>"{s}"</p>
                  ))}
                </div>
              )}
            </div>

            {/* Party People */}
            {plan.party_people && plan.party_people.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontWeight: '600', color: '#D1D5DB', marginBottom: '0.5rem' }}>🙌 Party People</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {plan.party_people.map((name, i) => (
                    <span key={i} style={{ 
                      padding: '0.25rem 0.5rem', 
                      backgroundColor: 'rgba(236, 72, 153, 0.5)', 
                      borderRadius: '9999px', 
                      fontSize: '0.875rem' 
                    }}>
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Cultural Phrases */}
            {plan.cultural_phrases && Object.keys(plan.cultural_phrases).length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontWeight: '600', color: '#D1D5DB', marginBottom: '0.5rem' }}>🌍 Cultural Vibes</h3>
                {Object.entries(plan.cultural_phrases).map(([lang, phrases]) => (
                  <div key={lang} style={{ marginBottom: '0.5rem' }}>
                    <p style={{ fontSize: '0.75rem', color: '#A78BFA', textTransform: 'capitalize' }}>{lang}</p>
                    <p style={{ fontSize: '0.875rem', color: '#9CA3AF' }}>{phrases.join(' • ')}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Approve Button */}
            <button
              onClick={handleApprove}
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                background: 'linear-gradient(to right, #7C3AED, #EC4899)',
                borderRadius: '0.5rem',
                fontWeight: 'bold',
                fontSize: '1.125rem',
                border: 'none',
                color: 'white',
                cursor: 'pointer'
              }}
            >
              Approve &amp; Generate 🎧
            </button>
          </div>
        ) : (
          // Empty State
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
            <div style={{ textAlign: 'center', color: '#6B7280' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>✨</div>
              <p>Your playlist plan will appear here</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
