import { useEffect, useState } from 'react';
import { getAdversarialProbe, getLocations } from '../api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts';
import { GitMerge, Play, Activity, ShieldAlert, CheckCircle } from 'lucide-react';

export default function AdversarialProbe() {
  const [form, setForm] = useState({ user_id: 2, amount: 8000, hour: 1, location: 'Dubai', merchant: 'LuxuryMall' });
  const [results, setResults] = useState(null);
  const [animatingIdx, setAnimatingIdx] = useState(0);
  const [running, setRunning] = useState(false);
  const [locations, setLocations] = useState([]);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      try {
        const res = await getLocations({ user_id: String(form.user_id) });
        if (!mounted) return;
        const locs = res.locations || [];
        setLocations(locs);
        if (locs.length > 0 && !locs.includes(form.location)) {
          setForm(prev => ({ ...prev, location: locs[0] }));
        }
      } catch (_err) {
        // Fallback: keep existing default location.
        if (!mounted) return;
        console.debug('Failed to load locations:', _err);
        setLocations(['Mumbai', 'Delhi', 'Bangalore', 'London', 'Dubai']);
      }
    };
    run();
    return () => { mounted = false; };
  }, [form.user_id]);

  const runProbe = async () => {
    setRunning(true);
    setResults(null);
    setAnimatingIdx(0);
    try {
      // Mock D string
      const d = new Date(); d.setHours(form.hour);
      const payload = { ...form, timestamp: d.toISOString() };
      
      const res = await getAdversarialProbe(payload);
      setResults(res.probe_results);
      
      // Animate line chart
      let idx = 0;
      const int = setInterval(() => {
        idx++;
        setAnimatingIdx(idx);
        if (idx >= res.probe_results.length) clearInterval(int);
      }, 800);
      
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  const getBadgeStyle = (d) => {
    if (d === 'APPROVE') return 'bg-decision-approve/20 text-decision-approve';
    if (d === 'WARN') return 'bg-decision-warn/20 text-decision-warn';
    if (d === 'DELAY') return 'bg-decision-delay/20 text-decision-delay';
    if (d === 'BLOCK') return 'bg-decision-block/20 text-decision-block';
    return '';
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center border-b border-border pb-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><GitMerge className="text-primary"/> Adversarial Probe</h1>
          <p className="text-secondary mt-1 tracking-wider uppercase text-xs">Simulated attack mutation modeling</p>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-2 space-y-4">
           <div className="card-finguard">
             <h2 className="text-sm font-bold border-b border-border pb-2 mb-4">Base Transaction Trajectory</h2>
             
             <div className="space-y-4 text-sm">
               <div>
                 <label className="block text-secondary mb-1">Target User ID</label>
                 <select value={form.user_id} onChange={e => setForm({...form, user_id: parseInt(e.target.value)})}
                    className="w-full bg-background border border-border rounded p-2 text-primary focus:outline-none focus:border-decision-block">
                    <option value="1">User 1 (Aman - Standard Profile)</option>
                    <option value="2">User 2 (Riya - High Range Profile)</option>
                    <option value="3">User 3 (Kabir - Irregular Profile)</option>
                 </select>
               </div>
               <div>
                 <label className="block text-secondary mb-1">Injection Amount (₹)</label>
                 <input type="number" value={form.amount} onChange={e => setForm({...form, amount: parseFloat(e.target.value)})}
                    className="w-full bg-background border border-border rounded p-2 text-primary font-mono focus:outline-none focus:border-decision-block" />
               </div>
               <div className="flex gap-2">
                 <div className="flex-1">
                   <label className="block text-secondary mb-1">Hour</label>
                   <input type="number" value={form.hour} onChange={e => setForm({...form, hour: parseInt(e.target.value)})}
                      className="w-full bg-background border border-border rounded p-2 text-primary text-center focus:outline-none focus:border-decision-block" />
                 </div>
                 <div className="flex-[2]">
                   <label className="block text-secondary mb-1">Location Context</label>
                   <select
                     value={form.location}
                     onChange={e => setForm({ ...form, location: e.target.value })}
                     className="w-full bg-background border border-border rounded p-2 text-primary focus:outline-none focus:border-decision-block"
                   >
                     {(locations.length > 0 ? locations : ['Mumbai', 'Delhi', 'Bangalore', 'London', 'Dubai']).map(l => (
                       <option key={l} value={l}>{l}</option>
                     ))}
                   </select>
                 </div>
               </div>
             </div>

             <button onClick={runProbe} disabled={running} className="w-full mt-6 bg-decision-block/10 hover:bg-decision-block/20 text-decision-block border border-decision-block/50 font-bold py-3 px-4 rounded flex items-center justify-center gap-2 transition-colors">
               {running ? <Activity className="w-5 h-5 animate-spin"/> : <Play className="w-5 h-5"/>}
               {running ? 'Fuzzing...' : 'Init Mutation Sequence'}
             </button>
           </div>
           
           <div className="card-finguard p-4 bg-muted/10 border-dashed border-2 text-xs text-secondary leading-relaxed">
             The adversarial probe applies synthetic data mutations against the live ML manifold. It simulates attacker techniques (velocities, location hopping, amount scaling) sequentially, proving real-time barrier elasticity under dynamic load.
           </div>
        </div>

        <div className="col-span-3">
           {!results ? (
             <div className="card-finguard h-[500px] flex flex-col justify-center items-center text-center text-secondary p-8">
               <ShieldAlert className="w-16 h-16 opacity-20 mb-4 text-decision-block" />
               <p>Awaiting probe parameters. Configure payload and initialize mutation sequence.</p>
             </div>
           ) : (
             <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
               <div className="card-finguard h-[300px]">
                 <h3 className="text-sm font-bold border-b border-border pb-2 mb-2">Sequence Risk Trajectory</h3>
                 <ResponsiveContainer width="100%" height="90%">
                   <LineChart lineData={results} data={results.slice(0, animatingIdx)} margin={{top: 10, right: 10, left: -20, bottom: 5}}>
                     <XAxis dataKey="step" tick={{fontSize: 10, fill: '#8b949e'}} />
                     <YAxis domain={[0, 130]} tick={{fontSize: 10, fill: '#8b949e'}} />
                     <Tooltip contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}} cursor={{stroke: '#21262d'}}/>
                     <ReferenceArea y1={75} y2={130} fill="#f85149" fillOpacity={0.1} />
                     <ReferenceArea y1={55} y2={75} fill="#f0883e" fillOpacity={0.1} />
                     <ReferenceArea y1={0} y2={55} fill="#3fb950" fillOpacity={0.1} />
                     <Line type="monotone" dataKey="risk_score" stroke="#58a6ff" strokeWidth={3} dot={{fill: '#0d1117', stroke: '#58a6ff', strokeWidth: 2, r: 4}} isAnimationActive={true}/>
                   </LineChart>
                 </ResponsiveContainer>
               </div>
               
               <div className="card-finguard">
                 <table className="w-full text-left text-sm whitespace-nowrap">
                   <thead className="bg-background text-secondary">
                     <tr>
                       <th className="p-3 font-medium">Mutation Step</th>
                       <th className="p-3 font-medium text-right">Risk Force</th>
                       <th className="p-3 font-medium">Decision Vector</th>
                     </tr>
                   </thead>
                   <tbody className="divide-y divide-border/50">
                     {results.slice(0, animatingIdx).map((r, i) => (
                       <tr key={i} className="animate-in slide-in-from-left-2">
                         <td className="p-3 font-mono text-primary">{r.step}</td>
                         <td className="p-3 text-right">
                           <span className="font-bold flex items-center justify-end gap-2">{Math.round(r.risk_score)}</span>
                         </td>
                         <td className="p-3">
                           <span className={`px-2 py-1 rounded text-xs font-bold ${getBadgeStyle(r.decision)}`}>
                             {r.decision}
                           </span>
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
               
               {animatingIdx === results.length && (
                 <div className="bg-decision-approve/10 border border-decision-approve/30 p-4 rounded-lg flex items-center gap-3">
                   <div className="bg-decision-approve/20 p-2 rounded-full">
                     <CheckCircle className="w-6 h-6 text-decision-approve" />
                   </div>
                   <div>
                     <p className="text-sm text-primary font-medium">Probe Sequence Complete</p>
                     <p className="text-xs text-secondary mt-1">Manifold exhibited {results[0].risk_score > results[results.length-1].risk_score ? 'positive elasticity' : 'escalated defense validation'}. Engine successfully adjusted block matrices dynamically.</p>
                   </div>
                 </div>
               )}
             </div>
           )}
        </div>
      </div>
    </div>
  );
}
