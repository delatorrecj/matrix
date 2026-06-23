"use client";

import { Play, Pause, SkipBack, SkipForward, Calendar, Maximize, ChevronDown } from "lucide-react";
import { useState } from "react";

interface PlaybackBarProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  time?: number;
  maxTime?: number;
  onTimeChange?: (time: number) => void;
  startLabel?: string;
  endLabel?: string;
}

const SPEED_OPTIONS = ["0.5x", "1x", "2x", "4x"];

export function PlaybackBar({
  isPlaying,
  onTogglePlay,
  time = 0,
  maxTime = 1000,
  onTimeChange,
  startLabel = "06:00",
  endLabel = "22:00",
}: PlaybackBarProps) {
  const [speed, setSpeed] = useState("1x");
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);

  return (
    <div className="glass-strong h-14 rounded-xl flex items-center px-4 gap-4">
      {/* Transport controls */}
      <div className="flex items-center gap-1.5">
        <button
          aria-label="Skip back"
          className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
        >
          <SkipBack className="w-4 h-4" />
        </button>
        <button
          onClick={onTogglePlay}
          aria-label={isPlaying ? "Pause" : "Play"}
          className="w-10 h-10 flex items-center justify-center bg-primary text-white rounded-full hover:bg-primary-hover transition-colors shadow-md"
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>
        <button
          aria-label="Skip forward"
          className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
        >
          <SkipForward className="w-4 h-4" />
        </button>
      </div>

      {/* Timeline slider */}
      <div className="flex-1 flex items-center gap-3">
        <span className="text-xs font-mono font-medium text-text-muted w-10 text-right">{startLabel}</span>
        <div className="flex-1 relative">
          <input
            type="range"
            min="0"
            max={maxTime > 0 ? maxTime : 1000}
            value={time}
            onChange={(e) => onTimeChange?.(Number(e.target.value))}
            className="w-full"
            aria-label="Timeline position"
          />
        </div>
        <span className="text-xs font-mono font-medium text-text-muted w-10">{endLabel}</span>
      </div>

      {/* Select Time button */}
      <button
        aria-label="Select time"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
      >
        <Calendar className="w-3.5 h-3.5" />
        <span>Select Time</span>
      </button>

      {/* Speed selector */}
      <div className="relative">
        <button
          onClick={() => setShowSpeedMenu(!showSpeedMenu)}
          aria-label="Playback speed"
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border text-xs font-mono font-medium text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
        >
          {speed}
          <ChevronDown className="w-3 h-3" />
        </button>
        {showSpeedMenu && (
          <div className="absolute bottom-full mb-1 right-0 bg-surface border border-border rounded-lg shadow-lg overflow-hidden z-50">
            {SPEED_OPTIONS.map((opt) => (
              <button
                key={opt}
                onClick={() => { setSpeed(opt); setShowSpeedMenu(false); }}
                className={`block w-full px-4 py-1.5 text-xs font-mono text-left transition-colors ${
                  opt === speed
                    ? "bg-primary/10 text-primary"
                    : "text-text-muted hover:bg-surface-elevated hover:text-text"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Fullscreen toggle */}
      <button
        aria-label="Toggle fullscreen"
        className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
        onClick={() => {
          if (document.fullscreenElement) {
            void document.exitFullscreen();
          } else {
            void document.documentElement.requestFullscreen();
          }
        }}
      >
        <Maximize className="w-4 h-4" />
      </button>
    </div>
  );
}
