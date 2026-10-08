/**
 * Centralized API client for ECHO Backend
 */

const API_BASE = '';

/**
 * Fetch all memories with optional filtering and search
 */
export async function fetchMemories({ category, search, person } = {}) {
  const params = new URLSearchParams();
  if (category && category !== 'all') params.append('category', category);
  if (search && search.trim()) params.append('search', search.trim());
  if (person && person.trim()) params.append('person', person.trim());

  const url = `/api/memories${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch memories: ${response.status}`);
  }
  return await response.json();
}

/**
 * Ingest a manual text statement into the memory pipeline
 */
export async function createManualMemory(text) {
  const response = await fetch('/api/memories/manual', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: text.trim() }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create memory: ${response.status}`);
  }
  return await response.json();
}

/**
 * Ingest recorded audio Blob to backend for STT & memory extraction
 */
export async function uploadAudio(audioBlob, filename = 'recording.webm') {
  const formData = new FormData();
  formData.append('file', audioBlob, filename);

  const response = await fetch('/api/audio/ingest', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Audio ingestion failed: ${response.status}`);
  }
  return await response.json();
}

/**
 * Query ECHO memories with grounded recall and SerpApi web search
 */
export async function queryEcho(query, enableWebGrounding = true) {
  const response = await fetch('/api/memories/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query.trim(),
      enable_web_grounding: enableWebGrounding,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Query failed: ${response.status}`);
  }
  return await response.json();
}

/**
 * Delete a memory by its ID
 */
export async function deleteMemory(id) {
  const response = await fetch(`/api/memories/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete memory: ${response.status}`);
  }
  return await response.json();
}

/**
 * Get backend system and API key status
 */
export async function getHealth() {
  const response = await fetch('/api/health');
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return await response.json();
}
