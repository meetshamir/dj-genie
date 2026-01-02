import { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface PlanData {
  ready?: boolean;
  theme?: string;
  mood?: string[];
  languages?: string[];
  duration_minutes?: number;
  songs?: { title: string; artist: string; why?: string }[];
  commentary_samples?: string[];
  shoutouts?: string[];
}

const API_BASE = "";

// Helper to format message content - strip JSON code blocks
function formatMessageContent(content: string): React.ReactNode {
  // Match ```json ... ``` blocks (with optional whitespace)
  const jsonBlockRegex = /```json[\s\S]*?```/g;
  const withoutJson = content.replace(jsonBlockRegex, "").trim();

  if (!withoutJson) {
    return "✅ Plan ready! Check the panel on the right →";
  }

  return withoutJson;
}

export default function AIPlaylistPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hey! 🎉 I'm your AI DJ assistant. Tell me about your party - what's the occasion, what languages or genres do you want, and what vibe are you going for? Let's create something amazing!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [editableShoutouts, setEditableShoutouts] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + "px";
    }
  }, [input]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/ai-chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = "";

      if (reader) {
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === "content") {
                  assistantMessage += data.content;
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1] = { role: "assistant", content: assistantMessage };
                    return newMsgs;
                  });
                } else if (data.type === "plan") {
                  setPlan(data.plan);
                  setEditableShoutouts(data.plan.shoutouts || []);
                } else if (data.type === "done") {
                  if (data.session_id) setSessionId(data.session_id);
                } else if (data.type === "error") {
                  setError(data.error);
                }
              } catch {
                /* ignore partial JSON */
              }
            }
          }
        }
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Failed to send message";
      setError(errMsg);
      console.error("Chat error:", err);
      setMessages((prev) => [...prev, { role: "system", content: `❌ Error: ${errMsg}` }]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  };

  const approvePlan = async () => {
    if (!sessionId || !plan) {
      setError("No plan to approve. Chat with me first to create a plan!");
      return;
    }
    setIsLoading(true);
    setError(null);
    setExportStatus("approving");

    try {
      const response = await fetch(`${API_BASE}/api/ai-chat/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          modifications: { shoutouts: editableShoutouts },
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Approve failed: ${errText}`);
      }

      const data = await response.json();

      if (data.job_id) {
        setExportStatus("connecting");
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `🚀 Plan approved! Starting export with job ID: ${data.job_id}`,
          },
        ]);

        // Connect to WebSocket for progress
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/export/${data.job_id}`;

        try {
          const ws = new WebSocket(wsUrl);

          ws.onopen = () => {
            setExportStatus("connected");
          };

          ws.onmessage = (event) => {
            try {
              const msg = JSON.parse(event.data);
              setProgress(msg.progress || 0);
              setExportStatus(msg.status || "processing");

              if (msg.status === "complete" && msg.result?.output_path) {
                setExportResult(msg.result.output_path);
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "system",
                    content: `🎉 Your mix is ready! File: ${msg.result.output_path}`,
                  },
                ]);
              } else if (msg.status === "failed") {
                setError(msg.error || "Export failed");
              }
            } catch {
              console.error("WS parse error");
            }
          };

          ws.onerror = () => {
            console.error("WebSocket error");
            setError("WebSocket connection failed. Check if the server is running.");
            setExportStatus(null);
          };

          ws.onclose = () => {
            console.log("WebSocket closed");
          };
        } catch {
          console.error("WS connection error");
          setError("Failed to connect to export progress. The export may still be running.");
        }
      } else {
        setMessages((prev) => [...prev, { role: "system", content: "✅ Plan approved!" }]);
        setExportStatus(null);
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Failed to approve";
      setError(errMsg);
      setExportStatus(null);
    } finally {
      setIsLoading(false);
    }
  };

  const yoloGenerate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/ai-chat/yolo`, { method: "POST" });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`YOLO failed: ${errText}`);
      }

      const data = await response.json();
      if (data.success) {
        setSessionId(data.session_id);
        setMessages((prev) => [...prev, { role: "system", content: `🎲 ${data.message}` }]);
        setPlan({
          ready: true,
          theme: data.theme,
          mood: ["energetic", "fun"],
          duration_minutes: 20,
        });
      } else {
        setError(data.error || "YOLO failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "YOLO failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>✨ AI DJ Studio</h1>
        <p style={styles.subtitle}>Tell me about your party and I'll create the perfect mix</p>
        <a href="/" style={styles.backLink}>← Back to main app</a>
      </header>

      <div style={styles.mainContent}>
        <div style={styles.chatPanel}>
          <div style={styles.messagesContainer}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  ...styles.message,
                  ...(msg.role === "user" ? styles.userMessage : styles.assistantMessage),
                  ...(msg.role === "system" ? styles.systemMessage : {}),
                }}
              >
                {msg.role === "assistant" ? formatMessageContent(msg.content) : msg.content}
              </div>
            ))}
            {isLoading && <div style={styles.loadingIndicator}>⏳ Thinking...</div>}
            <div ref={messagesEndRef} />
          </div>

          {error && <div style={styles.error}>⚠️ {error}</div>}

          <div style={styles.inputContainer}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your party... (Ctrl+Enter to send)"
              style={styles.textarea}
              disabled={isLoading}
              rows={3}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              style={{
                ...styles.sendButton,
                opacity: isLoading || !input.trim() ? 0.5 : 1,
              }}
            >
              Send
            </button>
          </div>

          <div style={styles.quickActions}>
            <button onClick={yoloGenerate} disabled={isLoading} style={styles.yoloButton}>
              🎲 YOLO - Random Mix!
            </button>
          </div>
        </div>

        <div style={styles.planPanel}>
          <h2 style={styles.planTitle}>📋 Your Mix Plan</h2>
          {plan ? (
            <div style={styles.planContent}>
              <div style={styles.planSection}>
                <strong>Theme:</strong> {plan.theme || "TBD"}
              </div>
              <div style={styles.planSection}>
                <strong>Mood:</strong> {plan.mood?.join(", ") || "TBD"}
              </div>
              <div style={styles.planSection}>
                <strong>Languages:</strong> {plan.languages?.join(", ") || "TBD"}
              </div>
              <div style={styles.planSection}>
                <strong>Duration:</strong> {plan.duration_minutes || 30} minutes
              </div>
              {plan.songs && plan.songs.length > 0 && (
                <div style={styles.planSection}>
                  <strong>Songs ({plan.songs.length}):</strong>
                  <ul style={styles.songList}>
                    {plan.songs.map((song, i) => (
                      <li key={i}>
                        <strong>{song.title}</strong> - {song.artist}
                        {song.why && <div style={styles.songReason}>↳ {song.why}</div>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div style={styles.planSection}>
                <strong>Shoutouts:</strong>
                {editableShoutouts.map((shoutout, i) => (
                  <input
                    key={i}
                    type="text"
                    value={shoutout}
                    onChange={(e) => {
                      const ns = [...editableShoutouts];
                      ns[i] = e.target.value;
                      setEditableShoutouts(ns);
                    }}
                    style={styles.shoutoutInput}
                  />
                ))}
                <button
                  onClick={() => setEditableShoutouts([...editableShoutouts, ""])}
                  style={styles.addShoutoutBtn}
                >
                  + Add Shoutout
                </button>
              </div>
              <button
                onClick={approvePlan}
                disabled={isLoading}
                style={{
                  ...styles.approveButton,
                  opacity: isLoading ? 0.5 : 1,
                }}
              >
                {isLoading ? "⏳ Processing..." : "✅ Approve & Generate!"}
              </button>
            </div>
          ) : (
            <p style={styles.noPlan}>
              Chat with me to build your playlist plan. Once I have enough info, I'll show the plan
              here for you to review and edit.
            </p>
          )}
          {exportStatus && (
            <div style={styles.progressSection}>
              <strong>Export Status:</strong> {exportStatus}
              <div style={styles.progressBar}>
                <div style={{ ...styles.progressFill, width: `${progress}%` }} />
              </div>
              <span>{progress}%</span>
            </div>
          )}
          {exportResult && (
            <div style={styles.successBox}>
              🎉 <strong>Export Complete!</strong>
              <br />
              <code style={styles.filePath}>{exportResult}</code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#0f0f23",
    color: "#e0e0e0",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  header: {
    padding: "1rem 2rem",
    borderBottom: "1px solid #333",
    background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
  },
  title: { margin: 0, fontSize: "1.8rem", color: "#ffd700" },
  subtitle: { margin: "0.5rem 0 0", color: "#888" },
  backLink: { color: "#64b5f6", textDecoration: "none", fontSize: "0.9rem" },
  mainContent: {
    display: "flex",
    height: "calc(100vh - 120px)",
    gap: "1rem",
    padding: "1rem",
  },
  chatPanel: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#1a1a2e",
    borderRadius: "12px",
    overflow: "hidden",
  },
  messagesContainer: { flex: 1, overflowY: "auto", padding: "1rem" },
  message: {
    marginBottom: "1rem",
    padding: "0.75rem 1rem",
    borderRadius: "12px",
    maxWidth: "80%",
    whiteSpace: "pre-wrap",
    lineHeight: 1.5,
  },
  userMessage: { backgroundColor: "#4a90d9", marginLeft: "auto", color: "#fff" },
  assistantMessage: { backgroundColor: "#2d2d44", marginRight: "auto" },
  systemMessage: {
    backgroundColor: "#2d4a2d",
    margin: "0 auto",
    textAlign: "center",
    color: "#90EE90",
  },
  loadingIndicator: { color: "#888", padding: "0.5rem" },
  error: {
    backgroundColor: "#4a2d2d",
    color: "#ff6b6b",
    padding: "0.75rem",
    margin: "0 1rem",
    borderRadius: "8px",
  },
  inputContainer: {
    display: "flex",
    gap: "0.5rem",
    padding: "1rem",
    borderTop: "1px solid #333",
    alignItems: "flex-end",
  },
  textarea: {
    flex: 1,
    padding: "0.75rem",
    borderRadius: "8px",
    border: "1px solid #444",
    backgroundColor: "#2d2d44",
    color: "#fff",
    fontSize: "1rem",
    resize: "none",
    minHeight: "60px",
    maxHeight: "150px",
    lineHeight: 1.4,
    fontFamily: "inherit",
  },
  sendButton: {
    padding: "0.75rem 1.5rem",
    backgroundColor: "#4a90d9",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "1rem",
    fontWeight: "bold",
  },
  quickActions: {
    padding: "0.5rem 1rem 1rem",
    display: "flex",
    justifyContent: "center",
  },
  yoloButton: {
    padding: "0.5rem 1rem",
    backgroundColor: "#ff6b35",
    color: "#fff",
    border: "none",
    borderRadius: "20px",
    cursor: "pointer",
    fontSize: "0.9rem",
  },
  planPanel: {
    width: "380px",
    backgroundColor: "#1a1a2e",
    borderRadius: "12px",
    padding: "1rem",
    overflowY: "auto",
  },
  planTitle: { margin: "0 0 1rem", fontSize: "1.2rem", color: "#ffd700" },
  planContent: { fontSize: "0.9rem" },
  planSection: {
    marginBottom: "1rem",
    padding: "0.5rem",
    backgroundColor: "#2d2d44",
    borderRadius: "8px",
  },
  songList: { margin: "0.5rem 0 0", paddingLeft: "1.5rem", listStyle: "none" },
  songReason: { fontSize: "0.8rem", color: "#888", marginTop: "0.25rem" },
  shoutoutInput: {
    display: "block",
    width: "100%",
    padding: "0.5rem",
    marginTop: "0.5rem",
    borderRadius: "4px",
    border: "1px solid #444",
    backgroundColor: "#1a1a2e",
    color: "#fff",
    boxSizing: "border-box",
  },
  addShoutoutBtn: {
    marginTop: "0.5rem",
    padding: "0.25rem 0.5rem",
    backgroundColor: "transparent",
    color: "#64b5f6",
    border: "1px dashed #64b5f6",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.85rem",
  },
  approveButton: {
    width: "100%",
    padding: "1rem",
    backgroundColor: "#4caf50",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "1rem",
    fontWeight: "bold",
    marginTop: "1rem",
  },
  noPlan: { color: "#888", fontStyle: "italic" },
  progressSection: {
    marginTop: "1rem",
    padding: "0.5rem",
    backgroundColor: "#2d2d44",
    borderRadius: "8px",
  },
  progressBar: {
    height: "8px",
    backgroundColor: "#444",
    borderRadius: "4px",
    marginTop: "0.5rem",
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: "#4caf50",
    transition: "width 0.3s ease",
  },
  successBox: {
    marginTop: "1rem",
    padding: "1rem",
    backgroundColor: "#2d4a2d",
    borderRadius: "8px",
    color: "#90EE90",
  },
  filePath: {
    display: "block",
    marginTop: "0.5rem",
    fontSize: "0.8rem",
    color: "#fff",
    wordBreak: "break-all",
  },
};
