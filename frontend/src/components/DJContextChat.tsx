/**
 * DJ Context Chatbox Component
 * 
 * A chatbox-style UI for users to specify the party theme, mood, and preferences
 * for the AI DJ. Uses Azure OpenAI GPT to generate creative, contextual commentary.
 */

import React, { useState, useEffect } from 'react';
import { DJContext, saveDJContext, getDJContext } from '../api';

interface DJContextChatProps {
  playlistId: string;
  onContextSaved?: (context: DJContext) => void;
  className?: string;
}

// Preset themes for quick selection
const PRESET_THEMES = [
  { name: "New Year 2025 → 2026", theme: "New Year 2025 Party - Welcoming 2026!", mood: "energetic, celebratory, countdown vibes" },
  { name: "Summer Beach Party", theme: "Summer Beach Vibes Party", mood: "chill, sunny, tropical" },
  { name: "Bollywood Night", theme: "Bollywood Dhamaka Night", mood: "energetic, filmy, colorful" },
  { name: "Retro 80s/90s", theme: "Retro Hits Night - 80s & 90s Classics", mood: "nostalgic, fun, groovy" },
  { name: "Wedding Sangeet", theme: "Wedding Sangeet Celebration", mood: "romantic, festive, family fun" },
  { name: "House Party", theme: "Epic House Party", mood: "high-energy, fun, party vibes" },
];

// Suggested shoutouts
const SUGGESTED_SHOUTOUTS = [
  "Happy New Year!",
  "2026 here we come!",
  "Let's get this party started!",
  "Put your hands up!",
  "Make some noise!",
  "DJ dropping the beats!",
];

export const DJContextChat: React.FC<DJContextChatProps> = ({
  playlistId,
  onContextSaved,
  className = ""
}) => {
  const [context, setContext] = useState<DJContext>({
    theme: "New Year 2025 Party - Welcoming 2026!",
    mood: "energetic, celebratory, festive",
    audience: "party guests ready to dance",
    special_notes: "",
    custom_shoutouts: ["Happy New Year!", "2026 here we come!"]
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showShoutouts, setShowShoutouts] = useState(false);
  const [newShoutout, setNewShoutout] = useState("");

  // Load existing context when playlist changes
  useEffect(() => {
    if (playlistId) {
      loadContext();
    }
  }, [playlistId]);

  const loadContext = async () => {
    try {
      const existingContext = await getDJContext(playlistId);
      if (existingContext) {
        setContext(existingContext);
      }
    } catch (e) {
      // No existing context, use defaults
      console.log("No existing DJ context, using defaults");
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await saveDJContext(playlistId, context);
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
      onContextSaved?.(context);
    } catch (e) {
      setError("Failed to save DJ context");
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePresetSelect = (preset: typeof PRESET_THEMES[0]) => {
    setContext((prev: DJContext) => ({
      ...prev,
      theme: preset.theme,
      mood: preset.mood
    }));
    setIsSaved(false);
  };

  const addShoutout = (shoutout: string) => {
    if (shoutout.trim() && !context.custom_shoutouts?.includes(shoutout.trim())) {
      setContext((prev: DJContext) => ({
        ...prev,
        custom_shoutouts: [...(prev.custom_shoutouts || []), shoutout.trim()]
      }));
      setNewShoutout("");
      setIsSaved(false);
    }
  };

  const removeShoutout = (index: number) => {
    setContext((prev: DJContext) => ({
      ...prev,
      custom_shoutouts: prev.custom_shoutouts?.filter((_: string, i: number) => i !== index) || []
    }));
    setIsSaved(false);
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">🎤</span>
        <h3 className="text-lg font-semibold text-white">AI DJ Settings</h3>
        <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full ml-auto">
          GPT-Powered
        </span>
      </div>

      {/* Preset Themes */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-2">Quick Presets</label>
        <div className="flex flex-wrap gap-2">
          {PRESET_THEMES.map((preset) => (
            <button
              key={preset.name}
              onClick={() => handlePresetSelect(preset)}
              className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                context.theme === preset.theme
                  ? "bg-purple-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Theme Input */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">
          Party Theme
          <span className="text-gray-500 ml-1">(What's the occasion?)</span>
        </label>
        <input
          type="text"
          value={context.theme}
          onChange={(e) => {
            setContext((prev: DJContext) => ({ ...prev, theme: e.target.value }));
            setIsSaved(false);
          }}
          placeholder="e.g., New Year 2025 Party - Welcoming 2026!"
          className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg focus:ring-2 focus:ring-purple-500 focus:outline-none"
        />
      </div>

      {/* Mood Input */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">
          Mood / Vibe
          <span className="text-gray-500 ml-1">(How should it feel?)</span>
        </label>
        <input
          type="text"
          value={context.mood}
          onChange={(e) => {
            setContext((prev: DJContext) => ({ ...prev, mood: e.target.value }));
            setIsSaved(false);
          }}
          placeholder="e.g., energetic, celebratory, festive"
          className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg focus:ring-2 focus:ring-purple-500 focus:outline-none"
        />
      </div>

      {/* Audience Input */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">
          Audience
          <span className="text-gray-500 ml-1">(Who's listening?)</span>
        </label>
        <input
          type="text"
          value={context.audience}
          onChange={(e) => {
            setContext((prev: DJContext) => ({ ...prev, audience: e.target.value }));
            setIsSaved(false);
          }}
          placeholder="e.g., party guests, friends, family"
          className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg focus:ring-2 focus:ring-purple-500 focus:outline-none"
        />
      </div>

      {/* Special Notes */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-1">
          Special Notes
          <span className="text-gray-500 ml-1">(Any special requests?)</span>
        </label>
        <textarea
          value={context.special_notes || ""}
          onChange={(e) => {
            setContext((prev: DJContext) => ({ ...prev, special_notes: e.target.value }));
            setIsSaved(false);
          }}
          placeholder="e.g., Reference Bollywood movies, mention SRK when Hindi songs play, etc."
          rows={2}
          className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg focus:ring-2 focus:ring-purple-500 focus:outline-none resize-none"
        />
      </div>

      {/* Custom Shoutouts */}
      <div className="mb-4">
        <button
          onClick={() => setShowShoutouts(!showShoutouts)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <span>{showShoutouts ? "▼" : "▶"}</span>
          Custom Shoutouts ({context.custom_shoutouts?.length || 0})
        </button>
        
        {showShoutouts && (
          <div className="mt-2 space-y-2">
            {/* Current shoutouts */}
            <div className="flex flex-wrap gap-2">
              {context.custom_shoutouts?.map((shoutout: string, index: number) => (
                <span
                  key={index}
                  className="bg-gray-700 text-white px-2 py-1 rounded-full text-sm flex items-center gap-1"
                >
                  {shoutout}
                  <button
                    onClick={() => removeShoutout(index)}
                    className="text-gray-400 hover:text-red-400 ml-1"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            {/* Add new shoutout */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newShoutout}
                onChange={(e) => setNewShoutout(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addShoutout(newShoutout)}
                placeholder="Add a shoutout..."
                className="flex-1 bg-gray-700 text-white px-3 py-1.5 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"
              />
              <button
                onClick={() => addShoutout(newShoutout)}
                className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 transition-colors"
              >
                Add
              </button>
            </div>

            {/* Suggested shoutouts */}
            <div className="flex flex-wrap gap-1">
              {SUGGESTED_SHOUTOUTS.filter(s => !context.custom_shoutouts?.includes(s)).map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => addShoutout(suggestion)}
                  className="text-xs bg-gray-700 text-gray-400 px-2 py-1 rounded hover:bg-gray-600 hover:text-white transition-colors"
                >
                  + {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-4 text-red-400 text-sm bg-red-900/30 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={isLoading}
        className={`w-full py-2 rounded-lg font-semibold transition-colors ${
          isSaved
            ? "bg-green-600 text-white"
            : "bg-purple-600 text-white hover:bg-purple-700"
        } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        {isLoading ? "Saving..." : isSaved ? "✓ Saved!" : "Save DJ Settings"}
      </button>

      {/* Info */}
      <p className="mt-3 text-xs text-gray-500 text-center">
        The AI DJ will use GPT-4 to generate creative, themed commentary
        that references song artists, Bollywood stars, and your theme!
      </p>
    </div>
  );
};

export default DJContextChat;
