import { useState, useEffect, useRef } from 'react';
import { getWsUrl } from '../api';
import { Activity, ShieldCheck, AlertTriangle, AlertCircle, TrendingUp } from 'lucide-react';
import { LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function LiveFeed() {
  const [txns, setTxns] = useState([]);
  const [status, setStatus] = useState('Connecting...');
  const [tpm, setTpm] = useState(0);
  const [fraudRate, setFraudRate] = useState(0);
  const wsRef = useRef(null);
  
  const COLORS = { APPROVE: '#3fb950', WARN: '#d29922', DELAY: '#f0883e', BLOCK: '#f85149' };

  useEffect(() => {
    let reconnectTimer;
    const connect = () => {
      setStatus('Connecting...');
      wsRef.current = new WebSocket(getWsUrl());
      
      wsRef.current.onopen = () => {
        setStatus('Connected');
      };
      
      wsRef.current.onmessage = (e) => {
        try {
          const t = JSON.parse(e.data);
          setTxns(prev => {
            const next = [t, ...prev].slice(0, 50);
            return next;
          });
        } catch (parseErr) {
          // If backend sends an unexpected payload, don't break the whole page.
          console.debug('LiveFeed WS message parse error:', parseErr);
        }
      };
      
      wsRef.current.onclose = () => {
        setStatus('Disconnected - Reconnecting...');
        reconnectTimer = setTimeout(connect, 3000);
      };
    };
    
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      clearTimeout(reconnectTimer);
    };
  }, []);

  // TPM Calculation loop
  useEffect(() => {
    const int = setInterval(() => {
      const now = new Date();
      const recentTxns = txns.filter(t => (now - new Date(t.timestamp)) < 60000);
      setTpm(recentTxns.length);
      
      const total = txns.length;
      if (total > 0) {
        const fraud = txns.filter(t => ['BLOCK', 'DELAY'].includes(t.decision)).length;
        setFraudRate(((fraud / total) * 100).toFixed(1));
      } else {
        setFraudRate(0);
      }
    }, 2000);
    return () => clearInterval(int);
  }, [txns]);

  // Derived charts logic
  const getDonutData = () => {
    let d = { 'Unknown Location': 0, 'Night': 0, 'Rapid/Velocity': 0, 'Round Amount': 0, 'Other': 0 };
    txns.filter(t => ['BLOCK', 'DELAY'].includes(t.decision)).forEach(t => {
      const f = t.features_used;
      if (!f) return;
      if (f.is_rapid) d['Rapid/Velocity']++;
      else if (f.is_unknown_location) d['Unknown Location']++;
      else if (f.is_night) d['Night']++;
      else if (f.is_round_amount) d['Round Amount']++;
      else d['Other']++;
    });
    return Object.entries(d).filter(([, v]) => v > 0).map(([k, v]) => ({ name: k, value: v }));
  };

  const lineData = txns.slice().reverse().map((t, i) => ({
    name: i,
    risk: t.risk_score,
    decision: t.decision
  }));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-border pb-4">
        <div>
          <h1 className="text-3xl font-bold text-primary flex items-center gap-3">
            Live Stream Intercept
            {tpm > 80 && <span className="bg-decision-block text-white text-xs px-2 py-1 rounded animate-pulse">BURST MODE</span>}
          </h1>
          <p className="text-secondary mt-1">Real-time asynchronous inspection</p>
        </div>
        <div className="flex gap-4">
          <div className="card-finguard px-4 py-2 flex flex-col justify-center items-end min-w-[120px]">
             <span className="text-xs text-secondary">TPM</span>
             <span className="text-xl font-mono text-primary">{tpm}</span>
          </div>
          <div className="card-finguard px-4 py-2 flex flex-col justify-center items-end min-w-[120px]">
             <span className="text-xs text-secondary">Fraud Vol</span>
             <span className={`text-xl font-mono ${fraudRate > 10 ? 'text-decision-block' : 'text-decision-warn'}`}>{fraudRate}%</span>
          </div>
          <div className="card-finguard px-4 py-2 flex items-center gap-3">
             <div className={`w-3 h-3 rounded-full ${status === 'Connected' ? 'bg-decision-approve' : 'bg-decision-block'}`}></div>
             <span className="text-sm font-semibold text-secondary">{status}</span>
          </div>
        </div>
      </div>

      <div className="card-finguard overflow-hidden overflow-x-auto min-h-[400px]">
         <table className="w-full text-left text-sm whitespace-nowrap">
           <thead className="bg-background border-b border-border text-secondary">
             <tr>
               <th className="p-3 font-medium">Time</th>
               <th className="p-3 font-medium">User</th>
               <th className="p-3 font-medium text-right">Amount (₹)</th>
               <th className="p-3 font-medium">Merchant</th>
               <th className="p-3 font-medium">Decision</th>
               <th className="p-3 font-medium">Risk Score</th>
             </tr>
           </thead>
           <tbody className="divide-y divide-border/50">
             {txns.length === 0 && <tr><td colSpan="6" className="text-center p-8 text-secondary">Waiting for payload...</td></tr>}
             {txns.map((t, i) => (
               <tr key={i} className={`animate-in fade-in slide-in-from-top-2 hover:bg-surface/60 transition-colors ${['BLOCK', 'DELAY'].includes(t.decision) ? 'border-l-4 border-l-decision-block' : 'border-l-4 border-l-transparent'}`}>
                 <td className="p-3 text-muted font-mono">{t.timestamp.split('T')[1]?.split('.')[0] || 'Now'}</td>
                 <td className="p-3">
                   <span className="font-semibold" style={{color: (t.user_id%2===0 ? '#58a6ff' : '#bc8cff')}}>User {t.user_id}</span>
                 </td>
                 <td className="p-3 text-right font-mono">{Number(t.amount).toLocaleString('en-IN', {minimumFractionDigits:2})}</td>
                 <td className="p-3 text-secondary">{t.merchant}</td>
                 <td className="p-3">
                   <span className="text-xs font-bold px-2 py-1 rounded" style={{color: COLORS[t.decision], backgroundColor: `${COLORS[t.decision]}20`}}>{t.decision}</span>
                 </td>
                 <td className="p-3">
                   <div className="w-full max-w-[100px] h-1.5 bg-background rounded-full overflow-hidden">
                     <div className="h-full transition-all" style={{width: `${Math.min(t.risk_score, 100)}%`, backgroundColor: COLORS[t.decision]}}></div>
                   </div>
                 </td>
               </tr>
             ))}
           </tbody>
         </table>
      </div>

      {txns.length > 10 && (
        <div className="grid grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4">
          <div className="card-finguard flex flex-col h-[300px]">
            <h3 className="text-sm font-semibold border-b border-border pb-2 mb-2">Fraud Vector Topography</h3>
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={getDonutData()} innerRadius={60} outerRadius={90} dataKey="value" stroke="none">
                    {getDonutData().map((e, index) => <Cell key={index} fill={Object.values(COLORS)[index % 4]} />)}
                  </Pie>
                  <Tooltip contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap text-xs gap-3 justify-center mb-2">
               {getDonutData().map((e, index) => (
                 <div key={e.name} className="flex gap-1 items-center">
                   <span className="w-2 h-2 rounded-full" style={{background: Object.values(COLORS)[index % 4]}}></span>
                   <span className="text-secondary">{e.name} ({e.value})</span>
                 </div>
               ))}
            </div>
          </div>
          
          <div className="card-finguard flex flex-col h-[300px]">
            <h3 className="text-sm font-semibold border-b border-border pb-2 mb-2">Risk Trajectory (Last 50)</h3>
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData} margin={{top: 10, right: 10, left: -20, bottom: 0}}>
                  <XAxis dataKey="name" hide />
                  <YAxis type="number" domain={[0, 130]} stroke="#484f58" tick={{fontSize: 10, fill: '#8b949e'}} />
                  <Tooltip contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}} cursor={{stroke: '#21262d'}}/>
                  <Line type="monotone" dataKey="risk" stroke="#58a6ff" strokeWidth={2} dot={false} activeDot={{r: 4}} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
