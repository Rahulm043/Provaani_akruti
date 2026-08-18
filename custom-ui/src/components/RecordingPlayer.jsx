import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Download, Volume2, VolumeX, Headphones, Loader2 } from 'lucide-react';
import { formatDuration, API_BASE } from '../utils/api.js';

export default function RecordingPlayer({ publicToken, runId, defaultDuration }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(defaultDuration || 0);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [srcError, setSrcError] = useState(false);
  const audioRef = useRef(null);

  const initialSrc = publicToken
    ? `${API_BASE}/api/v1/public/download/workflow/${publicToken}/recording`
    : runId
    ? `${API_BASE}/voice-audio/recordings/${runId}.wav`
    : null;

  const [activeSrc, setActiveSrc] = useState(initialSrc);

  useEffect(() => {
    const nextSrc = publicToken
      ? `${API_BASE}/api/v1/public/download/workflow/${publicToken}/recording`
      : runId
      ? `${API_BASE}/voice-audio/recordings/${runId}.wav`
      : null;
    setActiveSrc(nextSrc);
    setSrcError(false);
    setIsLoading(true);
  }, [publicToken, runId]);

  const handleAudioError = () => {
    if (runId && activeSrc && !activeSrc.includes('/voice-audio/')) {
      setActiveSrc(`${API_BASE}/voice-audio/recordings/${runId}.wav`);
    } else {
      setIsLoading(false);
      setSrcError(true);
    }
  };

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

  const handleDownload = (e) => {
    e.stopPropagation();
    if (!activeSrc) return;
    window.open(activeSrc, '_blank');
  };

  if (!activeSrc || srcError) {
    return (
      <div className="player-empty-state">
        <Headphones size={16} aria-hidden="true" className="player-empty-icon" />
        <span className="player-empty-text">Audio recording unavailable</span>
      </div>
    );
  }

  const progressPercent = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const sliderBg = `linear-gradient(to right, #6366f1 0%, #6366f1 ${progressPercent}%, rgba(255, 255, 255, 0.12) ${progressPercent}%, rgba(255, 255, 255, 0.12) 100%)`;

  return (
    <div className="simple-audio-player">
      <audio
        ref={audioRef}
        src={activeSrc}
        preload="auto"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        onLoadStart={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
        onError={handleAudioError}
      />

      <button
        className="simple-play-btn"
        onClick={togglePlay}
        disabled={isLoading}
        title={isPlaying ? 'Pause audio' : 'Play audio'}
        aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
        type="button"
      >
        {isLoading ? (
          <Loader2 size={15} className="spinner-loader" aria-hidden="true" />
        ) : isPlaying ? (
          <Pause size={15} aria-hidden="true" />
        ) : (
          <Play size={15} fill="currentColor" style={{ marginLeft: 1.5 }} aria-hidden="true" />
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
          onTouchStart={() => setIsScrubbing(true)}
          onTouchEnd={() => setIsScrubbing(false)}
          disabled={isLoading}
          aria-label="Audio playback seeker"
        />
      </div>

      <span className="simple-time" aria-live="off">
        {isLoading ? '0s' : `${formatDuration(currentTime)} / ${formatDuration(duration)}`}
      </span>

      <button
        className="simple-icon-btn"
        onClick={toggleMute}
        title={isMuted ? 'Unmute' : 'Mute'}
        aria-label={isMuted ? 'Unmute' : 'Mute'}
        type="button"
      >
        {isMuted ? <VolumeX size={15} aria-hidden="true" /> : <Volume2 size={15} aria-hidden="true" />}
      </button>

      <button
        className="simple-icon-btn"
        onClick={handleDownload}
        title="Download audio recording"
        aria-label="Download audio recording"
        type="button"
      >
        <Download size={15} aria-hidden="true" />
      </button>
    </div>
  );
}

