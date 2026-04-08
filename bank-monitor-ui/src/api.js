const rawApiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const API_URL = rawApiUrl.replace('localhost', '127.0.0.1');
const WS_URL = API_URL.replace('http', 'ws');

export async function getRecentTransactions(params = {}) {
  const q = new URLSearchParams(params);
  const res = await fetch(`${API_URL}/transactions/recent?${q.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function scoreTransaction(payload) {
  const res = await fetch(`${API_URL}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to score transaction');
  return res.json();
}

export function getWsUrl() {
  return `${WS_URL}/ws/live_feed`;
}
