const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function sendChat({ message, threadId }) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId || null })
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Chat request failed');
  }
  return res.json();
}

export async function resumeChat({ threadId, approved, feedback }) {
  const res = await fetch(`${API_URL}/api/chat/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, approved, feedback })
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Resume request failed');
  }
  return res.json();
}
