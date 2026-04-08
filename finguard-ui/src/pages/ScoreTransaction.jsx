import { useState } from 'react';
import { scoreTransaction, getExplanation } from '../api';
import { Activity, ShieldAlert, CheckCircle, Clock, XCircle, ChevronDown, ChevronUp, Search, Brain } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const USERS = [
  { id: 1, name: 'Aman', color: 'border-user-aman text-user-aman' },
  { id: 2, name: 'Riya', color: 'border-user-riya text-user-riya' },
  { id: 3, name: 'Kabir', color: 'border-user-kabir text-user-kabir' }
];

export default function ScoreTransaction() {
  const [form, setForm] = useState({ user_id: 1, amount: 500, hour: 14, location: 'Mumbai', merchant: 'Amazon' });
  const [result, setResult] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [expandAi, setExpandAi] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setExplanation(null);
    setError('');
    try {
      if (!Number.isFinite(form.amount) || form.amount <= 0) {
        throw new Error('Enter a valid amount greater than 0.');
      }
      if (!Number.isInteger(form.hour) || form.hour < 0 || form.hour > 23) {
        throw new Error('Hour must be between 0 and 23.');
      }
      if (!form.location || !form.merchant) {
        throw new Error('Location and merchant are required.');
      }

      // Build a stable UTC timestamp so selected hour is preserved exactly.
      const d = new Date();
      d.setUTCMinutes(0, 0, 0);
      d.setUTCHours(form.hour);
      const payload = {
        ...form,
        timestamp: d.toISOString(),
      };
      
      const res = await scoreTransaction(payload);
      setResult(res);
      
      setExplaining(true);
      try {
        const expRes = await getExplanation({
          transaction: payload,
          scoring_result: res
        });
        setExplanation(expRes.explanation);
      } catch (_err) {
        console.debug('Explanation request failed:', _err);
        setExplanation("AI Explanation is currently degraded.");
      } finally {
        setExplaining(false);
      }
      
    } catch (err) {
      console.error(err);
      setError(err?.message || 'Failed to score transaction.');
    } finally {
      setLoading(false);
    }
  };

  // Build SVG Gauge
  const renderGauge = (score) => {
    const min = 0;
    const max = 130;
    const norm = Math.min(Math.max((score - min) / (max - min), 0), 1);
    const angle = norm * 180;
    const r = 80;
    const cx = 100;
    const cy = 90;
    const rad = (Math.PI / 180) * (180 - angle);
    const nx = cx + (r - 10) * Math.cos(rad);
    const ny = cy - (r - 10) * Math.sin(rad);

    let color = '#3fb950';
    if (score >= 75) color = '#f85149';
    else if (score >= 55) color = '#f0883e';
    else if (score >= 30) color = '#d29922';

    return (
      <div className="relative w-[200px] h-[100px] mx-auto overflow-hidden">
        <svg viewBox="0 0 200 100" className="w-full h-full">
          <path d={`M 20 90 A 80 80 0 0 1 180 90`} fill="none" stroke="#21262d" strokeWidth="20" />
          <path d={`M 20 90 A 80 80 0 0 1 ${cx + 80*Math.cos(Math.PI - Math.PI*norm)} ${cy - 80*Math.sin(Math.PI - Math.PI*norm)}`} fill="none" stroke={color} strokeWidth="20" />
          <circle cx={cx} cy={cy} r="6" fill="#e6edf3" />
          <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#e6edf3" strokeWidth="4" strokeLinecap="round" />
        </svg>
        <div className="absolute top-[60px] left-1/2 -translate-x-1/2 text-center">
          <div className="font-bold text-3xl" style={{color}}>{Math.round(score)}</div>
        </div>
      </div>
    );
  };

  const getBadgeStyle = (d) => {
    if (d === 'APPROVE') return 'bg-decision-approve/20 text-decision-approve border-decision-approve/30';
    if (d === 'WARN') return 'bg-decision-warn/20 text-decision-warn border-decision-warn/30';
    if (d === 'DELAY') return 'bg-decision-delay/20 text-decision-delay border-decision-delay/30';
    if (d === 'BLOCK') return 'bg-decision-block/20 text-decision-block border-decision-block/30';
    return '';
  };
  
  const getIcon = (d) => {
    if (d === 'APPROVE') return <CheckCircle />;
    if (d === 'WARN') return <ShieldAlert />;
    if (d === 'DELAY') return <Clock />;
    if (d === 'BLOCK') return <XCircle />;
    return null;
  };

  return (
    <div className="grid grid-cols-5 gap-6">
      
      {/* Left Form Panel */}
      <div className="col-span-2 space-y-4">
        <div className="card-finguard">
          <h2 className="text-xl font-bold mb-4 border-b border-border pb-3">Score Transaction</h2>
          
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="text-xs text-decision-block bg-decision-block/10 border border-decision-block/30 rounded p-2">
                {error}
              </div>
            )}
            
            {/* User Details */}
            <div>
              <label className="block text-sm text-secondary mb-2">Select Target User</label>
              <div className="grid grid-cols-3 gap-3">
                {USERS.map(u => (
                  <button key={u.id} type="button" onClick={() => setForm({...form, user_id: u.id})} 
                    className={`p-3 rounded-lg border text-sm font-semibold transition-all ${form.user_id === u.id ? `${u.color} bg-surface` : 'border-border text-secondary hover:border-muted'}`}>
                    {u.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Amount */}
            <div>
              <label className="block text-sm text-secondary mb-1">Amount (₹)</label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-secondary">₹</span>
                <input type="number" value={form.amount} onChange={e => setForm({...form, amount: parseFloat(e.target.value) || 0})}
                  className="w-full bg-background border border-border rounded-lg p-2.5 pl-8 text-primary focus:outline-none focus:border-user-aman text-lg font-mono" />
              </div>
            </div>

            {/* Hour Dropdown Slider proxy */}
            <div>
              <div className="flex justify-between items-end mb-1">
                <label className="text-sm text-secondary">Hour of Day</label>
                <span className="text-xs text-muted font-mono">{form.hour}:00</span>
              </div>
              <input type="range" min="0" max="23" value={form.hour} onChange={e => setForm({...form, hour: parseInt(e.target.value)})}
                className="w-full accent-user-aman bg-border h-2 rounded-lg appearance-none" />
            </div>

            {/* Time Gap Override */}
            <div>
              <label className="block text-sm text-secondary mb-1">Time Since Last Txn (Seconds Override)</label>
              <input type="number" placeholder="Auto-calculated if empty" value={form.time_gap_override || ''} onChange={e => setForm({...form, time_gap_override: e.target.value ? parseFloat(e.target.value) : undefined})}
                className="w-full bg-background border border-border rounded-lg p-2.5 text-primary focus:outline-none focus:border-user-aman font-mono" />
              <p className="text-xs text-muted mt-1">Force test velocity rules (e.g. 5 seconds for rapid txn)</p>
            </div>

            {/* Location & Merchant */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-secondary mb-1">Location Context</label>
                <select value={form.location} onChange={e => setForm({...form, location: e.target.value})}
                  className="w-full bg-background border border-border rounded-lg p-2.5 text-primary focus:outline-none focus:border-user-aman">
                  <optgroup label="Known Habitual Cities">
                    <option value="Mumbai">Mumbai</option>
                    <option value="Delhi">Delhi</option>
                    <option value="Bangalore">Bangalore</option>
                    <option value="London">London</option>
                    <option value="Dubai">Dubai</option>
                  </optgroup>
                  <optgroup label="High Risk / Unknown">
                    <option value="Russia">Russia</option>
                    <option value="China">China</option>
                    <option value="Nigeria">Nigeria</option>
                    <option value="Offshore">Offshore Island</option>
                  </optgroup>
                </select>
              </div>
              <div>
                <label className="block text-sm text-secondary mb-1">Merchant</label>
                <select value={form.merchant} onChange={e => setForm({...form, merchant: e.target.value})}
                  className="w-full bg-background border border-border rounded-lg p-2.5 text-primary focus:outline-none focus:border-user-aman">
                  <optgroup label="Low/Medium Risk">
                    <option value="Amazon">Amazon</option>
                    <option value="Swiggy">Swiggy</option>
                    <option value="Zomato">Zomato</option>
                    <option value="Flipkart">Flipkart</option>
                    <option value="BookStore">BookStore</option>
                  </optgroup>
                  <optgroup label="High Risk Destinations">
                    <option value="Steam">Steam</option>
                    <option value="EpicGames">EpicGames</option>
                    <option value="Airline">Airline</option>
                    <option value="Hotel">Hotel</option>
                    <option value="LuxuryMall">LuxuryMall</option>
                    <option value="Unknown_Crypto">Unknown Crypto Exchange</option>
                  </optgroup>
                </select>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-decision-approve hover:bg-[#329e41] text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50">
              {loading ? <Activity className="animate-spin" /> : <Search />}
              {loading ? 'Scoring Engine Active...' : 'Score Transaction'}
            </button>
          </form>
        </div>
      </div>

      {/* Right Results Panel */}
      <div className="col-span-3">
        {!result ? (
          <div className="card-finguard h-full flex flex-col items-center justify-center text-secondary">
            <ShieldAlert className="w-16 h-16 opacity-20 mb-4" />
            <p>Enter parameters and execute scoring to populate intelligence.</p>
          </div>
        ) : (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
            
            {/* Banner */}
            <div className={`p-4 rounded-xl border flex justify-between items-center ${getBadgeStyle(result.decision)}`}>
              <div className="flex items-center gap-3">
                {getIcon(result.decision)}
                <div>
                  <h3 className="font-bold text-lg tracking-wide">{result.decision}</h3>
                  <p className="text-sm opacity-80">Enforcement threshold matched</p>
                </div>
              </div>
              <div>{renderGauge(result.risk_score)}</div>
            </div>

            {/* AI Explanation Banner */}
            <div className={`card-finguard transition-all duration-300 ${expandAi ? 'py-4' : 'py-3 cursor-pointer hover:bg-surface/80'}`} onClick={() => !expandAi && setExpandAi(true)}>
              <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-2 font-semibold bg-gradient-to-r from-decision-delay to-user-aman bg-clip-text text-transparent">
                  <Brain className="w-5 h-5 text-user-aman" /> AI Explanation
                </div>
                {explaining ? <Activity className="w-4 h-4 animate-spin text-secondary" /> : 
                  (expandAi ? <ChevronUp className="w-5 h-5 cursor-pointer text-secondary" onClick={(e) => {e.stopPropagation(); setExpandAi(false);}} /> : <ChevronDown className="w-5 h-5 text-secondary" />)}
              </div>
              {expandAi && (
                <div className="mt-3 text-sm text-secondary leading-relaxed bg-background p-3 rounded border border-border whitespace-pre-line">
                  {explaining ? 'Generating explanation from model signals...' : explanation}
                </div>
              )}
            </div>

            {/* Models 2x2 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="card-finguard p-4">
                <div className="text-xs text-secondary mb-2 uppercase tracking-wider">XGBoost Prob</div>
                <div className="h-2 w-full bg-background rounded overflow-hidden">
                  <div className="h-full bg-decision-block transition-all" style={{width: `${(result.models.xgboost_prob * 100).toFixed(1)}%`}}></div>
                </div>
                <div className="mt-1 text-right text-sm font-mono text-primary">{(result.models.xgboost_prob * 100).toFixed(1)}%</div>
              </div>

              <div className="card-finguard p-4">
                <div className="text-xs text-secondary mb-2 uppercase tracking-wider">Random Forest Prob</div>
                <div className="h-2 w-full bg-background rounded overflow-hidden">
                  <div className="h-full bg-decision-warn transition-all" style={{width: `${(result.models.random_forest_prob * 100).toFixed(1)}%`}}></div>
                </div>
                <div className="mt-1 text-right text-sm font-mono text-primary">{(result.models.random_forest_prob * 100).toFixed(1)}%</div>
              </div>

              <div className="card-finguard p-4">
                <div className="text-xs text-secondary mb-2 uppercase tracking-wider">LSTM Seq Prob</div>
                <div className="h-2 w-full bg-background rounded overflow-hidden">
                  <div className="h-full bg-decision-delay transition-all" style={{width: `${(result.models.lstm_prob * 100).toFixed(1)}%`}}></div>
                </div>
                <div className="mt-1 text-right text-sm font-mono text-primary">{(result.models.lstm_prob * 100).toFixed(1)}%</div>
              </div>

              <div className="card-finguard p-4">
                <div className="text-xs text-secondary mb-2 uppercase tracking-wider">Autoencoder Recon Error</div>
                <div className="text-sm">
                  {result.autoencoder.reconstruction_error.toFixed(6)}
                  <span className="text-muted ml-1">vs {result.autoencoder.threshold.toFixed(6)} threshold</span>
                </div>
                <div className="mt-1 text-[11px] text-muted">
                  Rule: anomaly if reconstruction error {'>'} threshold.
                </div>
                <div className={`mt-1 text-xs font-bold ${result.autoencoder.is_anomaly ? 'text-decision-block' : 'text-decision-approve'}`}>
                  {result.autoencoder.is_anomaly ? 'ANOMALY DETECTED' : 'NORMAL'}
                </div>
              </div>
            </div>

            {/* SHAP section */}
            <div className="card-finguard">
               <h3 className="text-sm font-bold border-b border-border pb-2 mb-3">SHAP Vector Contributions</h3>
               <div className="h-[120px]">
                 {result.shap_explanation && (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={
                          Object.entries(result.shap_explanation.shap_values)
                          .map(([k,v]) => ({name: k, value: v}))
                          .sort((a,b) => Math.abs(b.value) - Math.abs(a.value))
                          .slice(0, 5)
                      } layout="vertical" margin={{top: 5, right: 30, left: 20, bottom: 5}}>
                        <XAxis type="number" hide />
                        <YAxis dataKey="name" type="category" width={120} tick={{fontSize: 10, fill: '#8b949e'}} />
                        <Tooltip contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}}/>
                        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                          {Object.entries(result.shap_explanation.shap_values)
                           .map(([k,v]) => ({name: k, value: v}))
                           .sort((a,b) => Math.abs(b.value) - Math.abs(a.value))
                           .slice(0, 5)
                           .map((entry, index) => (
                             <Cell key={`cell-${index}`} fill={entry.value > 0 ? '#f85149' : '#3fb950'} />
                           ))
                          }
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                 )}
               </div>
            </div>
            
            <div className="text-right">
              <span className="bg-background border border-border text-muted text-xs px-2 py-1 rounded-full">
                Latency: {result.latency_ms}ms
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
