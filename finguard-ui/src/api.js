const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http', 'ws');

export const scoreTransaction = async (payload) => {
  const res = await fetch(`${API_URL}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to score transaction');
  return res.json();
};

export const getDashboardStats = async () => {
  const res = await fetch(`${API_URL}/dashboard_stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
};

export const getRecentTransactions = async (params = {}) => {
  const searchParams = new URLSearchParams(params);
  const url = `${API_URL}/transactions/recent?${searchParams.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
};

export const getAdversarialProbe = async (payload) => {
  const res = await fetch(`${API_URL}/adversarial_probe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to run probe');
  return res.json();
};

export const getModelMetrics = async () => {
  const res = await fetch(`${API_URL}/model_metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
};

export const getGlobalShap = async () => {
  const res = await fetch(`${API_URL}/global_shap`);
  if (!res.ok) throw new Error('Failed to fetch SHAP');
  return res.json();
};

export const getDriftReport = async () => {
  const res = await fetch(`${API_URL}/drift_report`);
  if (!res.ok) throw new Error('Failed to fetch drift report');
  return res.json();
};

export const runDriftCheck = async () => {
  const res = await fetch(`${API_URL}/run_drift_check`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run drift check');
  return res.json();
};

export const getGraphData = async () => {
  const res = await fetch(`${API_URL}/graph_data`);
  if (!res.ok) throw new Error('Failed to fetch graph data');
  return res.json();
};

export const getLocations = async (params = {}) => {
  const searchParams = new URLSearchParams(params);
  const url = `${API_URL}/locations?${searchParams.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch locations');
  return res.json();
};

export const getExplanation = async (payloadOrTxnId) => {
  const isObjectPayload = payloadOrTxnId !== null && typeof payloadOrTxnId === 'object';
  const res = await fetch(
    isObjectPayload ? `${API_URL}/explain_decision` : `${API_URL}/explain/${payloadOrTxnId}`,
    {
      method: isObjectPayload ? 'POST' : 'GET',
      headers: isObjectPayload ? { 'Content-Type': 'application/json' } : undefined,
      body: isObjectPayload ? JSON.stringify(payloadOrTxnId) : undefined
    }
  );
  if (!res.ok) throw new Error('Failed to fetch explanation');
  return res.json();
};

export const getWsUrl = () => {
  return `${WS_URL}/ws/live_feed`;
};
