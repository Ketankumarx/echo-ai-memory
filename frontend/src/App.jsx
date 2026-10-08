import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { AudioRecorder } from './components/AudioRecorder';
import { MemoryFeed } from './components/MemoryFeed';
import { AskEcho } from './components/AskEcho';
import { ShieldCheckIcon, SparklesIcon } from './components/Icons';

export function App() {
  const [memories, setMemories] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoadingMemories, setIsLoadingMemories] = useState(true);

  // Fetch real memories from SQLite on startup
  const loadMemories = useCallback(async () => {
    try {
      const response = await fetch('/api/memories');
      if (response.ok) {
        const data = await response.json();
        setMemories(data);
      }
    } catch (err) {
      console.error("Failed to load memories from backend:", err);
    } finally {
      setIsLoadingMemories(false);
    }
  }, []);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  // Called when new memory/memories are extracted via audio or manual note
  const handleMemoryAdded = (newMemories) => {
    const memoryList = Array.isArray(newMemories) ? newMemories : [newMemories];
    setMemories(prev => {
      const existingIds = new Set(prev.map(m => m.id));
      const toAdd = memoryList.filter(m => !existingIds.has(m.id));
      return [...toAdd, ...prev];
    });
  };

  // Delete memory permanently from SQLite and UI
  const handleDeleteMemory = async (id) => {
    // Optimistic UI update
    setMemories(prev => prev.filter(m => m.id !== id));

    try {
      const response = await fetch(`/api/memories/${id}`, {
        method: 'DELETE'
      });
      if (!response.ok) {
        console.error("Delete request failed on server, reloading...");
        loadMemories();
      }
    } catch (err) {
      console.error("Failed to delete memory:", err);
      loadMemories();
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <Header
        isRecording={isRecording}
        memoryCount={memories.length}
      />

      {/* Main 2-Column Dashboard Grid */}
      <main className="dashboard-grid">
        {/* Left Column: Voice Capture & Memory Stream */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <AudioRecorder
            onRecordingChange={setIsRecording}
            onMemoryAdded={handleMemoryAdded}
          />

          <MemoryFeed
            memories={memories}
            isLoading={isLoadingMemories}
            onDeleteMemory={handleDeleteMemory}
          />
        </div>

        {/* Right Column: Ask ECHO Conversational Recall */}
        <div>
          <AskEcho memories={memories} />
        </div>
      </main>

      {/* Footer / Hackathon Consent & Branding */}
      <footer className="app-footer">
        <span>
          <ShieldCheckIcon size={14} />
          ECHO Personal AI Memory • Explicit Consent Capture Only
        </span>
        <span>•</span>
        <span>
          <SparklesIcon size={14} />
          Hackathon MVP Edition
        </span>
      </footer>
    </div>
  );
}

export default App;
