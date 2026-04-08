import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Clock3, MapPin, ShieldAlert, Timer, User, Wallet } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getRecentTransactions, getWsUrl, scoreTransaction } from './api';

const DECISION_STYLE = { APPROVE: 'ok', WARN: 'warn', DELAY: 'delay', BLOCK: 'block' };

function decisionIcon(decision) {
  if (decision === 'BLOCK') return <ShieldAlert size={14} />;
  if (decision === 'DELAY') return <Clock3 size={14} />;
  if (decision === 'WARN') return <AlertTriangle size={14} />;
  return <CheckCircle2 size={14} />;
}

export default function App() {
  const [activeTab, setActiveTab] = useState('backend');
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState('Connecting...');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [form, setForm] = useState({
    user_id: 1, payee_name: 'Amazon Seller', upi_id: 'amazon@upi', amount: 1200, location: 'Mumbai', hour: 14
  });
  const [upiResult, setUpiResult] = useState(null);
  const [error, setError] = useState('');
  const [networkError, setNetworkError] = useState('');
  const [flowStep, setFlowStep] = useState('entry'); // entry -> pin -> result
  const [pin, setPin] = useState('');

  useEffect(() => {
    const loadInitial = async () => {
      try {
        const txns = await getRecentTransactions({ limit: 40 });
        const normalized = Array.isArray(txns) ? txns : [];
        setRows(normalized);
        if (normalized.length > 0) setSelected(normalized[0]);
        setNetworkError('');
      } catch (err) {
        setNetworkError(err?.message || 'Backend not reachable.');
      } finally {
        setLoading(false);
      }
    };
    loadInitial();
  }, []);

  useEffect(() => {
    let ws;
    let reconnectTimer;
    const connect = () => {
      setStatus('Connecting...');
      ws = new WebSocket(getWsUrl());
      ws.onopen = () => setStatus('Live');
      ws.onmessage = (e) => {
        try {
          const t = JSON.parse(e.data);
          setRows(prev => [t, ...prev].slice(0, 100));
          setSelected(t);
        } catch {
          // Ignore malformed frame.
        }
      };
      ws.onclose = () => {
        setStatus('Disconnected');
        reconnectTimer = setTimeout(connect, 2500);
      };
      ws.onerror = () => {
        setStatus('Error');
        setNetworkError('WebSocket disconnected. Waiting for backend...');
      };
    };
    connect();
    return () => {
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
      clearTimeout(reconnectTimer);
    };
  }, []);

  const highRiskCount = useMemo(() => rows.filter(r => ['WARN', 'DELAY', 'BLOCK'].includes(r.decision)).length, [rows]);
  const avgAmount = useMemo(() => {
    if (!rows.length) return 0;
    const sum = rows.reduce((acc, r) => acc + Number(r.amount || 0), 0);
    return sum / rows.length;
  }, [rows]);

  const simplifiedReasons = useMemo(() => {
    if (!upiResult) return [];
    const out = [];
    const f = upiResult.features_used || {};
    const shap = upiResult.shap_explanation?.shap_values || {};
    const topKeys = Object.keys(shap).slice(0, 6);
    const hasAmount = topKeys.includes('amount_vs_avg') || Number(f.amount_vs_avg || 1) > 2;
    const hasLocation = topKeys.includes('is_unknown_location') || Number(f.is_unknown_location || 0) === 1;
    const hasRapid = topKeys.includes('time_since_last_txn') || Number(f.is_rapid || 0) === 1;
    const hasNight = topKeys.includes('is_night') || Number(f.is_night || 0) === 1;
    if (hasAmount) out.push({ icon: <Wallet size={14} />, text: 'This amount is unusually high compared to your past transactions.' });
    if (hasLocation) out.push({ icon: <MapPin size={14} />, text: 'This transaction is being made from a new or unusual location.' });
    if (hasRapid) out.push({ icon: <Timer size={14} />, text: 'This payment happened very quickly after a recent transaction.' });
    if (hasNight) out.push({ icon: <AlertTriangle size={14} />, text: 'This transaction timing is unusual for your account.' });
    for (const r of upiResult.reasons || []) {
      if (out.length >= 3) break;
      out.push({ icon: <AlertTriangle size={14} />, text: r });
    }
    return out.slice(0, 3);
  }, [upiResult]);

  const graphData = useMemo(() => [
    { name: 'Your Average', value: Number(avgAmount.toFixed(2)) },
    { name: 'Current Txn', value: Number(upiResult?.amount || form.amount || 0) }
  ], [avgAmount, upiResult, form.amount]);

  async function onSendMoney(e) {
    e.preventDefault();
    setFlowStep('pin');
    setError('');
  }

  async function onConfirmPin(e) {
    e.preventDefault();
    if (!/^\d{4}$/.test(pin)) {
      setError('Enter a valid 4-digit UPI PIN.');
      return;
    }
    setSubmitting(true);
    setError('');
    setShowDetails(false);
    try {
      const d = new Date();
      d.setUTCMinutes(0, 0, 0);
      d.setUTCHours(Number(form.hour || 0));
      const payload = {
        user_id: Number(form.user_id || 1),
        amount: Number(form.amount || 0),
        timestamp: d.toISOString(),
        location: form.location,
        merchant: form.payee_name || 'UPI Payee'
      };
      const scored = await scoreTransaction(payload);
      setUpiResult(scored);
      setSelected(scored);
      setRows(prev => [scored, ...prev].slice(0, 100));
      setFlowStep('result');
    } catch (err) {
      setError(err?.message || 'Failed to send money.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>FinGuard UPI Simulation</h1>
          <p>Demo app with backend visibility and UPI user experience.</p>
        </div>
        <div className="status">
          <span className={`dot ${status === 'Live' ? 'live' : 'down'}`} />
          {status}
        </div>
      </div>

      {networkError && (
        <div className="net-error">{networkError}</div>
      )}

      <div className="tabs">
        <button className={`tab ${activeTab === 'backend' ? 'active' : ''}`} onClick={() => setActiveTab('backend')}>Simulation Backend View</button>
        <button className={`tab ${activeTab === 'upi' ? 'active' : ''}`} onClick={() => setActiveTab('upi')}>UPI User App</button>
      </div>

      {activeTab === 'backend' && (
        <>
          <div className="stats">
            <div className="card"><div className="k">Observed Payments</div><div className="v">{rows.length}</div></div>
            <div className="card"><div className="k">Needs Attention</div><div className="v warn-t">{highRiskCount}</div></div>
            <div className="card"><div className="k">Latest Payer</div><div className="v">User {selected?.user_id ?? '-'}</div></div>
            <div className="card"><div className="k">Latest Recipient</div><div className="v">{selected?.merchant ?? '-'}</div></div>
          </div>

          <div className="grid">
            <div className="panel">
              <h2>Incoming Payments Feed</h2>
              {loading ? (
                <div className="muted"><Activity size={14} className="spin" /> Loading...</div>
              ) : (
                <div className="list">
                  {rows.map((r, i) => (
                    <button key={`${r.timestamp || 't'}-${r.user_id || 'u'}-${i}`} type="button" onClick={() => setSelected(r)} className="row">
                      <div>
                        <div className="title">User {r.user_id} {'->'} {r.merchant}</div>
                        <div className="sub">Amount: INR {Number(r.amount || 0).toLocaleString('en-IN')} | Location: {r.location || '-'}</div>
                      </div>
                      <div className={`badge ${DECISION_STYLE[r.decision] || 'ok'}`}>{decisionIcon(r.decision)} {r.decision || 'APPROVE'}</div>
                    </button>
                  ))}
                  {rows.length === 0 && <div className="muted">No payments received yet.</div>}
                </div>
              )}
            </div>

            <div className="panel">
              <h2>Selected Transaction Details</h2>
              {!selected ? (
                <div className="muted">Select a payment from the feed.</div>
              ) : (
                <div className="stack">
                  <div className="box">
                    <div className="title"><User size={14} /> Payer User {selected.user_id}</div>
                    <div className="sub">Recipient: <b>{selected.merchant}</b></div>
                    <div className="sub">Amount: <b>INR {Number(selected.amount || 0).toLocaleString('en-IN')}</b></div>
                    <div className="sub">Location: <b>{selected.location || '-'}</b></div>
                    <div className="sub">Timestamp: <b>{selected.timestamp || '-'}</b></div>
                  </div>
                  <div className="box">
                    <div className="title">Risk Outcome</div>
                    <div className={`badge ${DECISION_STYLE[selected.decision] || 'ok'}`}>{decisionIcon(selected.decision)} {selected.decision || 'APPROVE'}</div>
                    <div className="sub">Risk Score: <b>{Math.round(selected.risk_score || 0)}</b></div>
                  </div>
                  <div className="box">
                    <div className="title">Why flagged</div>
                    {(selected.reasons || []).length > 0 ? (
                      <div className="reasons">{(selected.reasons || []).slice(0, 4).map(reason => <div key={reason}>- {reason}</div>)}</div>
                    ) : (
                      <div className="muted">No detailed reasons available for this row.</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {activeTab === 'upi' && (
        <div className="upi-wrap">
          <div className="phone">
            <div className="phone-header">
              <div>
                <div className="app-name">FinGuard Pay</div>
                <div className="user-line">User {form.user_id}</div>
              </div>
              <div className="avatar">FG</div>
            </div>

            <div className="payee-chip">
              <div className="avatar mini">{(form.payee_name || 'P').charAt(0).toUpperCase()}</div>
              <div>
                <div className="chip-name">{form.payee_name}</div>
                <div className="chip-upi">{form.upi_id}</div>
              </div>
            </div>

            {flowStep === 'entry' && (
              <form className="form" onSubmit={onSendMoney}>
                <label>Payee Name</label>
                <input value={form.payee_name} onChange={(e) => setForm({ ...form, payee_name: e.target.value })} />
                <label>UPI ID</label>
                <input value={form.upi_id} onChange={(e) => setForm({ ...form, upi_id: e.target.value })} />
                <label>Amount</label>
                <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })} />
                <label>Location</label>
                <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
                <button disabled={submitting} type="submit">Send Money</button>
                {error && <div className="err">{error}</div>}
              </form>
            )}

            {flowStep === 'pin' && (
              <form className="form pin-form" onSubmit={onConfirmPin}>
                <label>Enter UPI PIN</label>
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={4}
                  value={pin}
                  onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="****"
                />
                <button disabled={submitting} type="submit">{submitting ? 'Verifying...' : 'Confirm Payment'}</button>
                <button type="button" className="ghost-btn" onClick={() => setFlowStep('entry')}>Back</button>
                {error && <div className="err">{error}</div>}
              </form>
            )}

            {flowStep === 'result' && (
              <div className="form">
                <button type="button" onClick={() => { setFlowStep('entry'); setPin(''); }}>New Payment</button>
              </div>
            )}
          </div>

          <div className="result-panel">
            <h2>Transaction Result</h2>
            {!upiResult ? (
              <div className="muted">Send money to simulate fraud decision flow.</div>
            ) : (
              <>
                <div className={`decision-card ${DECISION_STYLE[upiResult.decision] || 'ok'}`}>
                  <div className="title">{decisionIcon(upiResult.decision)} {upiResult.decision}</div>
                  <div className="sub">Risk Score: <b>{Math.round(upiResult.risk_score || 0)}</b></div>
                  {upiResult.decision === 'APPROVE' && <div className="sub success-pop">Transaction Successful. This transaction appears normal.</div>}
                  {upiResult.decision === 'WARN' && <div className="sub">This transaction looks unusual.</div>}
                  {upiResult.decision === 'DELAY' && <div className="sub">Verification Required. Please complete OTP/confirmation.</div>}
                  {upiResult.decision === 'BLOCK' && <div className="sub">Transaction Blocked due to high fraud risk.</div>}
                </div>

                {upiResult.decision === 'BLOCK' && (
                  <div className="live-alert">Live Alert: Bank has been notified.</div>
                )}

                <div className="box">
                  <div className="title">Top 3 Reasons</div>
                  <div className="reasons">
                    {simplifiedReasons.map((r, i) => <div key={`${i}-${r.text}`}>{r.icon} {r.text}</div>)}
                  </div>
                </div>

                <div className="box">
                  <div className="title">Why this transaction was flagged</div>
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={graphData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                        <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
                        <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#58a6ff" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <button className="details-toggle" onClick={() => setShowDetails(v => !v)} type="button">
                  View Details {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {showDetails && (
                  <pre className="raw">{JSON.stringify({
                    decision: upiResult.decision,
                    risk_score: upiResult.risk_score,
                    fraud_probability: upiResult.fraud_probability,
                    reasons: upiResult.reasons,
                    shap_explanation: upiResult.shap_explanation,
                    features_used: upiResult.features_used
                  }, null, 2)}</pre>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
