import { useState, useEffect, useRef } from 'react';
import { MicIcon, SquareIcon, SparklesIcon, ActivityIcon, ShieldCheckIcon } from './Icons';
import { uploadAudio, createManualMemory } from '../api';

export const AudioRecorder = ({ onMemoryAdded, onMemoriesAdded, onRecordingChange }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [processingState, setProcessingState] = useState(null); // 'uploading' | 'transcribing' | 'extracting' | 'saving' | 'saved'
  const [errorMessage, setErrorMessage] = useState(null);
  const [quickInput, setQuickInput] = useState('');
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const canvasRef = useRef(null);
  const animFrameIdRef = useRef(null);

  const notifyMemoryAdded = (memories) => {
    if (onMemoriesAdded) onMemoriesAdded(memories);
    if (onMemoryAdded) onMemoryAdded(memories);
  };

  // Timer effect when recording
  useEffect(() => {
    let interval = null;
    if (isRecording) {
      interval = setInterval(() => {
        setTimerSeconds(prev => prev + 1);
      }, 1000);
    } else {
      setTimerSeconds(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);

  // Sync recording state to parent for Header badge
  useEffect(() => {
    if (onRecordingChange) {
      onRecordingChange(isRecording);
    }
  }, [isRecording, onRecordingChange]);

  // Audio Visualizer on Canvas (reactive to real microphone input)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      if (!isRecording) {
        // Flatline resting wave
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1.5;
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.stroke();
        return;
      }

      // Read real frequency data from microphone if AnalyserNode is available
      let frequencyMultiplier = 1.0;
      if (analyserRef.current) {
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((acc, val) => acc + val, 0);
        const avg = sum / (dataArray.length || 1);
        frequencyMultiplier = 0.5 + (avg / 128) * 1.5;
      }

      phase += 0.08;
      
      // Secondary background wave
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.4)';
      ctx.lineWidth = 2;
      for (let x = 0; x < width; x++) {
        const angle = (x / width) * Math.PI * 4 + phase * 0.7;
        const amplitude = (10 * frequencyMultiplier) * Math.sin(phase * 0.5 + x * 0.01);
        const y = centerY + Math.sin(angle) * amplitude;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Primary glowing crimson/rose wave
      ctx.beginPath();
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 2.5;
      ctx.shadowBlur = 12;
      ctx.shadowColor = 'rgba(244, 63, 94, 0.75)';

      for (let x = 0; x < width; x++) {
        const angle = (x / width) * Math.PI * 5 + phase;
        const amplitude = (height * 0.35 * frequencyMultiplier) * Math.sin(phase * 0.8 + x * 0.02);
        const y = centerY + Math.sin(angle) * amplitude;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      animFrameIdRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
    };
  }, [isRecording]);

  const formatTimer = (totalSec) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Start real microphone recording
  const handleStartRecording = async () => {
    setErrorMessage(null);
    setProcessingState(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      setErrorMessage("Audio recording is not supported in this browser environment.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 64;
          source.connect(analyser);
          audioContextRef.current = audioCtx;
          analyserRef.current = analyser;
        }
      } catch (audioCtxErr) {
        console.warn("AudioContext warning:", audioCtxErr);
      }

      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
      let selectedMime = '';
      for (const mime of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mime)) {
          selectedMime = mime;
          break;
        }
      }

      const recorder = selectedMime 
        ? new MediaRecorder(stream, { mimeType: selectedMime })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const mime = selectedMime || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mime });
        await handleAudioUpload(audioBlob);
      };

      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access error:", err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage("Microphone permission is required to record a memory.");
      } else {
        setErrorMessage(`Microphone error: ${err.message || 'Unable to access microphone'}`);
      }
    }
  };

  // Stop recording
  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }

    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  };

  // Upload recorded audio Blob to backend
  const handleAudioUpload = async (audioBlob) => {
    setProcessingState('uploading');
    setErrorMessage(null);

    try {
      setProcessingState('transcribing');
      const result = await uploadAudio(audioBlob, 'recording.webm');
      
      setProcessingState('extracting');
      await new Promise(r => setTimeout(r, 400));
      
      setProcessingState('saving');
      await new Promise(r => setTimeout(r, 300));
      
      setProcessingState('saved');
      if (result.memories) {
        notifyMemoryAdded(result.memories);
      }

      setTimeout(() => {
        setProcessingState(null);
      }, 3500);
    } catch (err) {
      console.error("Audio processing failed:", err);
      setProcessingState(null);
      setErrorMessage(err.message || "Failed to process audio.");
    }
  };

  // Quick manual memory submission (Demo Path)
  const handleQuickSubmit = async (e) => {
    e.preventDefault();
    const text = quickInput.trim();
    if (!text || isSubmittingManual) return;

    setIsSubmittingManual(true);
    setErrorMessage(null);
    setProcessingState('extracting');

    try {
      await new Promise(r => setTimeout(r, 300));
      setProcessingState('saving');
      const newMems = await createManualMemory(text);
      
      setProcessingState('saved');
      setQuickInput('');
      
      if (newMems) {
        notifyMemoryAdded(newMems);
      }

      setTimeout(() => {
        setProcessingState(null);
      }, 3000);
    } catch (err) {
      console.error("Manual memory creation failed:", err);
      setProcessingState(null);
      setErrorMessage(err.message || "Failed to add memory.");
    } finally {
      setIsSubmittingManual(false);
    }
  };

  return (
    <div className={`glass-panel recorder-card ${isRecording ? 'recording' : ''}`}>
      {/* Explicit 🔴 RECORDING Status Indicator */}
      {isRecording && (
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.35rem 0.85rem',
          background: 'rgba(244, 63, 94, 0.2)',
          border: '1px solid #f43f5e',
          borderRadius: '9999px',
          color: '#fecdd3',
          fontSize: '0.8rem',
          fontWeight: 700,
          marginBottom: '1rem',
          letterSpacing: '0.05em'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#f43f5e',
            boxShadow: '0 0 8px #f43f5e'
          }}></span>
          <span>🔴 RECORDING</span>
        </div>
      )}

      {/* Main Mic Button */}
      <div className="record-btn-wrapper">
        <div className="record-pulse-ring"></div>
        <button
          id="btn-toggle-record"
          className={`record-button ${isRecording ? 'active' : ''}`}
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          title={isRecording ? "Stop Recording" : "Start Recording"}
          aria-label={isRecording ? "Stop Recording" : "Start Recording"}
          disabled={Boolean(processingState && processingState !== 'saved')}
        >
          {isRecording ? <SquareIcon size={30} /> : <MicIcon size={34} />}
        </button>
      </div>

      {/* Dynamic Status Text */}
      <div className="recorder-status-text">
        {isRecording 
          ? "Recording in progress..." 
          : processingState === 'uploading'
          ? "Uploading audio..."
          : processingState === 'transcribing'
          ? "Transcribing speech..."
          : processingState === 'extracting'
          ? "Extracting memories..."
          : processingState === 'saving'
          ? "Saving memory..."
          : processingState === 'saved'
          ? "Memory saved ✓"
          : "Ready to Capture Conversation"}
      </div>

      {/* Timer */}
      <div className="recording-timer" id="recording-timer">
        {isRecording ? formatTimer(timerSeconds) : "00:00"}
      </div>

      {/* Dynamic Waveform Visualizer */}
      <div className="waveform-container">
        <canvas
          ref={canvasRef}
          width={400}
          height={64}
          className="waveform-canvas"
        />
        {!isRecording && (
          <div className="waveform-placeholder" style={{ position: 'absolute' }}>
            <ActivityIcon size={14} />
            <span>Voice Activity Visualizer (Idle)</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="recorder-actions">
        {isRecording ? (
          <button
            id="btn-stop-recording"
            className="btn-danger"
            onClick={handleStopRecording}
          >
            <SquareIcon size={14} />
            <span>Stop & Save Memory</span>
          </button>
        ) : (
          <button
            id="btn-start-recording"
            className="btn-primary"
            onClick={handleStartRecording}
            disabled={Boolean(processingState && processingState !== 'saved')}
          >
            <MicIcon size={16} />
            <span>Start Recording</span>
          </button>
        )}
      </div>

      {/* Friendly Error Display */}
      {errorMessage && (
        <div style={{
          marginTop: '1rem',
          padding: '0.65rem 1rem',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: '8px',
          color: '#fca5a5',
          fontSize: '0.78rem',
          textAlign: 'left',
          width: '100%',
          lineHeight: 1.4
        }}>
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Fast Manual Input Box */}
      <form onSubmit={handleQuickSubmit} className="quick-input-box" style={{ marginTop: '1.25rem' }}>
        <input
          id="input-quick-memory"
          type="text"
          className="text-input"
          placeholder="Or paste a spoken note (e.g. 'Rahul told me Friday 5 PM...')"
          value={quickInput}
          onChange={(e) => setQuickInput(e.target.value)}
          disabled={isRecording || isSubmittingManual}
        />
        <button 
          type="submit" 
          className="btn-secondary" 
          title="Add Memory Card"
          disabled={!quickInput.trim() || isSubmittingManual || isRecording}
        >
          <SparklesIcon size={14} />
          <span>{isSubmittingManual ? "Adding..." : "Add"}</span>
        </button>
      </form>

      {/* Explicit Consent Privacy Statement */}
      <div style={{
        marginTop: '1rem',
        fontSize: '0.72rem',
        color: 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        textAlign: 'center'
      }}>
        <ShieldCheckIcon size={13} style={{ color: 'var(--accent-emerald)' }} />
        <span>Your microphone is only accessed when you explicitly start recording.</span>
      </div>
    </div>
  );
};
