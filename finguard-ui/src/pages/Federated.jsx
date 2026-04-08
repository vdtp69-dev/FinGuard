import { useState } from 'react';
import { ShieldCheck, Database, RefreshCw, Lock, Activity, Server, FileText } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Federated() {
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState([]);
  const [finalRes, setFinalRes] = useState(null);
  const [round, setRound] = useState(0);
  const [error, setError] = useState(null);

  const startTraining = () => {
    setRunning(true);
    setHistory([]);
    setFinalRes(null);
    setRound(0);
    setError(null);

    // Using fetch directly because EventSource requires GET, but prompt asks for POST streaming
    // We will use Response stream reader
    fetch(`${API_URL}/federated/train`, { method: 'POST' })
      .then(async (res) => {
        if (!res.ok) {
          setError(`Federated training failed: ${res.status} ${res.statusText}`);
          setRunning(false);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (let line of lines) {
            if (!line.trim()) continue;
            try {
              const data = JSON.parse(line);
              if (data.status === 'training') {
                setRound(data.round);
                setHistory(prev => [...prev, { round: data.round, 'Federated AUC': data.auc, 'Centralized AUC': data.centralized_auc }]);
              } else if (data.status === 'complete') {
                setFinalRes(data);
                setRunning(false);
              }
            } catch (parseErr) {
              console.debug('Federated stream JSON parse error:', parseErr);
            }
          }
        }
        if (buffer.trim().length > 0) {
          try {
            const data = JSON.parse(buffer);
            if (data.status === 'complete') {
              setFinalRes(data);
              setRunning(false);
            }
          } catch {
            // Ignore incomplete trailing buffer.
          }
        }
      })
      .catch(err => {
        console.error(err);
        setError('Federated training failed. Check backend logs.');
        setRunning(false);
      });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-border pb-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><Database className="text-primary"/> Federated Network</h1>
          <p className="text-secondary mt-1 tracking-wider uppercase text-xs">Decentralized Embedded Training</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-1 space-y-4">
          <div className="card-finguard">
            <h2 className="text-lg font-semibold border-b border-border pb-2 mb-3">FedAvg Engine</h2>
            <p className="text-xs text-secondary leading-relaxed mb-4">
              Collaborative model sharing without data centralization. Banks transmit local coefficient updates (weights) to the aggregation node, where global policies are averaged and redistributed—keeping actual PII transaction data strictly within local silos.
            </p>
            <button onClick={startTraining} disabled={running} className="w-full bg-user-aman hover:bg-user-aman/90 text-background font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50">
              {running ? <Activity className="w-5 h-5 animate-spin"/> : <RefreshCw className="w-5 h-5"/>}
              {running ? `Epoch ${round}/10` : 'Execute Federated Training'}
            </button>
          </div>

          <div className="space-y-3">
             <div className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Node Isolation Logic</div>
             {[1, 2, 3].map(u => (
               <div key={u} className="card-finguard bg-background p-3 flex items-center gap-3">
                 <div className="bg-surface border border-border p-2 rounded shrink-0">
                   <Lock className="text-decision-approve w-4 h-4" />
                 </div>
                 <div>
                   <div className="text-sm font-semibold text-primary">Node {u} (Local Silo)</div>
                   <div className="text-xs text-secondary">PII & Amounts remain isolated</div>
                 </div>
               </div>
             ))}
             <div className="card-finguard bg-background p-3 flex items-center gap-3 mt-4 border-user-aman border-dashed border-2">
                 <div className="bg-user-aman/20 p-2 rounded shrink-0">
                   <Server className="text-user-aman w-4 h-4" />
                 </div>
                 <div>
                   <div className="text-sm font-semibold text-primary animate-pulse">Aggregation Server</div>
                   <div className="text-xs text-secondary">Averages W & B matrices</div>
                 </div>
             </div>
          </div>
        </div>

        <div className="col-span-2">
          {error && (
            <div className="card-finguard border-l-4 border-decision-block bg-decision-block/5 text-decision-block p-4 mb-4">
              {error}
            </div>
          )}
           <div className="card-finguard h-[400px]">
             <h3 className="text-sm font-semibold border-b border-border pb-2 mb-2">Federated vs Centralized Global AUC Convergence</h3>
             <ResponsiveContainer width="100%" height="85%">
               <LineChart data={history} margin={{top: 10, right: 10, left: -20, bottom: 5}}>
                 <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                 <XAxis dataKey="round" tick={{fontSize: 10, fill: '#8b949e'}} />
                 <YAxis domain={['auto', 'auto']} tick={{fontSize: 10, fill: '#8b949e'}} />
                 <Tooltip contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}} cursor={{stroke: '#21262d'}}/>
                 <Legend verticalAlign="top" height={36}/>
                 <Line type="step" dataKey="Centralized AUC" stroke="#484f58" strokeWidth={2} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                 <Line type="monotone" dataKey="Federated AUC" stroke="#58a6ff" strokeWidth={3} dot={{r:4, fill: '#161b22'}} isAnimationActive={false}/>
               </LineChart>
             </ResponsiveContainer>
           </div>
           
           {finalRes && (
             <div className="card-finguard mt-4 flex gap-6 items-center bg-surface animate-in slide-in-from-bottom-2">
               <div className="flex-1 bg-background p-4 rounded border border-border text-center">
                 <div className="text-xs uppercase text-secondary mb-1">Global Baseline (Unsafe)</div>
                 <div className="text-2xl font-mono opacity-80">{finalRes.centralized_auc.toFixed(4)}</div>
               </div>
               <div className="text-xl text-muted font-black uppercase tracking-[0.5em]">VS</div>
               <div className="flex-1 bg-decision-approve/10 p-4 rounded border border-decision-approve/30 text-center relative overflow-hidden">
                 <div className="absolute top-0 right-0 w-8 h-8 bg-decision-approve rotate-45 translate-x-4 -translate-y-4"></div>
                 <div className="text-xs uppercase text-decision-approve mb-1 font-bold tracking-wider">Federated Payload (Private)</div>
                 <div className="text-3xl font-mono font-bold text-primary">{finalRes.final_auc.toFixed(4)}</div>
               </div>
               
               <div className="flex-1 text-sm text-secondary">
                 Federated aggregation achieved a parity delta of <span className="text-primary font-bold">{Math.abs(finalRes.final_auc - finalRes.centralized_auc).toFixed(4)}</span> without transmitting a single localized transaction packet.
               </div>
             </div>
           )}
        </div>
      </div>
    </div>
  );
}
