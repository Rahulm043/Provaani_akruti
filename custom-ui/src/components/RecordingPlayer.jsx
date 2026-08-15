import React, { useState, useRef } from 'react';
import { Play, Pause, Download, Volume2, VolumeX, Headphones } from 'lucide-react';
import { formatDuration, API_BASE } from '../utils/api.js';

export default function RecordingPlayer({ publicToken, defaultDuration }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(defaultDuration || 0);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const audioRef = useRef(null);
  const audioSrc = publicToken ? `${API_BASE}/api/v1/public/download/workflow/${publicToken}/recording` : null;

  const handleTimeUpdate = () => {
    if (!isScrubbing && audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || defaultDuration || 0);
      setIsLoading(false);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || isLoading) return;
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().catch(console.error);
      setIsPlaying(true);
    }
  };

  const handleScrub = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleDownload = () => {
    if (!audioSrc) return;
    window.open(audioSrc, '_blank');
  };

  if (!publicToken) {
    return (
      <div style={{ padding: '0.75rem 1rem', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', textAlign: 'center' }}>
        <Headphones size={20} style={{ opacity: 0.3, marginBottom: '0.25rem' }} />
        <p className="text-sm text-dim">No recording available</p>
      </div>
    );
  }

  const progressPercent = duration ? (currentTime / duration) * 100 : 0;
  const sliderBg = `linear-gradient(to right, #6366f1 0%, #6366f1 ${progressPercent}%, rgba(255, 255, 255, 0.12) ${progressPercent}%, rgba(255, 255, 255, 0.12) 100%)`;

  return (
    <div className="simple-audio-player">
      <audio
        ref={audioRef}
        src={audioSrc}
        preload="auto"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        onLoadStart={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
      />

      <button
        className="simple-play-btn"
        onClick={togglePlay}
        disabled={isLoading}
        title={isPlaying ? 'Pause' : 'Play'}
        type="button"
      >
        {isLoading ? (
          <div className="spinner-loader" style={{ width: 14, height: 14 }} />
        ) : isPlaying ? (
          <Pause size={18} />
        ) : (
          <Play size={18} fill="currentColor" style={{ marginLeft: 2 }} />
        )}
      </button>

      <div className="simple-track-wrap">
        <input
          type="range"
          className="simple-slider"
          min={0}
          max={duration || 100}
          step={0.1}
          value={currentTime}
          style={{ background: sliderBg }}
          onChange={handleScrub}
          onMouseDown={() => setIsScrubbing(true)}
          onMouseUp={() => setIsScrubbing(false)}
          disabled={isLoading}
        />
      </div>

      <span className="simple-time">
        {isLoading ? '0s' : `${formatDuration(currentTime)} / ${formatDuration(duration)}`}
      </span>

      <button
        className="simple-icon-btn"
        onClick={toggleMute}
        title={isMuted ? 'Unmute' : 'Mute'}
        type="button"
      >
        {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
      </button>

      <button
        className="simple-icon-btn"
        onClick={handleDownload}
        title="Download recording"
        type="button"
      >
        <Download size={16} />
      </button>
    </div>
  );
}
