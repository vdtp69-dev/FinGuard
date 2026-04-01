import { useState, useEffect } from 'react';
import { getModelMetrics, getGlobalShap, getDriftReport, runDriftCheck } from '../api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Activity, ShieldCheck, AlertTriangle, AlertCircle, TrendingUp, RefreshCw, Clock, CheckCircle } from 'lucide-react';

export default function ModelIntelligence() {
  const [tab, setTab] = useState('performance');
  const [metrics, setMetrics] = useState(null);
  const [shap, setShap] = useState(null);
  const [drift, setDrift] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    Promise.all([
      getModelMetrics().catch(() => ({})),
      getGlobalShap().catch(() => ({})),
      getDriftReport().catch(() => ({}))
    ]).then(([m, s, d]) => {
      setMetrics(m);
      setShap(s);
      setDrift(d);
      setLoading(false);
    });
  }, []);

  const doDriftCheck = async () => {
    setChecking(true);
    try {
      const res = await runDriftCheck();
      setDrift(res);
    } catch (e) {
      console.error(e);
    }
    setChecking(false);
  };

  if (loading) return <div className="p-8 text-secondary"><Activity className="animate-spin inline mr-2"/> Compiling model intelligence...</div>;

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-4">
        <h1 className="text-3xl font-bold text-primary">Model Intelligence</h1>
        <p className="text-secondary mt-1">Audit, explainability, and drift detection capabilities</p>
      </div>

      <div className="flex gap-2 border-b border-border mb-6">
        {['performance', 'features', 'drift', 'costs'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 capitalize -mb-px border-b-2 font-medium transition-colors ${tab === t ? 'border-user-aman text-user-aman' : 'border-transparent text-secondary hover:text-primary'}`}>
            {t === 'costs' ? 'Cost Analysis' : t}
          </button>
        ))}
      </div>

      {tab === 'performance' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
           <div className="grid grid-cols-2 gap-6">
             <div className="card-finguard h-[400px]">
               <h3 className="text-sm font-semibold border-b border-border pb-2 mb-4">AUC-ROC Curve Comparison</h3>
               <ResponsiveContainer width="100%" height="85%">
                 <LineChart margin={{top: 5, right: 20, bottom: 5, left: 0}}>
                   <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                   <XAxis type="number" dataKey="fpr" name="FPR" tick={{fill: '#8b949e', fontSize: 12}} domain={[0,1]} />
                   <YAxis type="number" dataKey="tpr" name="TPR" tick={{fill: '#8b949e', fontSize: 12}} domain={[0,1]} />
                   <Tooltip cursor={{stroke: '#21262d'}} contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}}/>
                   <Legend verticalAlign="top" height={36}/>
                   <Line type="monotone" data={metrics?.roc_curve_xgboost || []} dataKey="tpr" stroke="#58a6ff" name={`XGBoost (AUC ${metrics?.xgboost?.auc_roc?.toFixed(3) || 'N/A'})`} dot={false} strokeWidth={2}/>
                   <Line type="monotone" data={metrics?.roc_curve_rf || []} dataKey="tpr" stroke="#bc8cff" name={`Random Forest (AUC ${metrics?.random_forest?.auc_roc?.toFixed(3) || 'N/A'})`} dot={false} strokeWidth={2}/>
                   <Line type="monotone" data={[{fpr:0, tpr:0}, {fpr:1, tpr:1}]} dataKey="tpr" stroke="#484f58" strokeDasharray="4 4" dot={false} name="Random" />
                 </LineChart>
               </ResponsiveContainer>
             </div>
             <div className="card-finguard h-[400px] flex justify-center items-center text-secondary">
               <div>
                  <h3 className="text-sm font-semibold mb-6 text-center text-primary">Confusion Matrix (XGBoost)</h3>
                  <div className="grid grid-cols-2 gap-2 text-center text-xl">
                    <div className="bg-decision-approve/20 text-decision-approve p-6 rounded-lg border border-decision-approve/30">
                       <div className="font-bold text-3xl">{metrics?.confusion_matrix?.[0]?.[0]?.toLocaleString() || '0'}</div>
                       <div className="text-xs mt-1 opacity-80 uppercase">True Negative</div>
                    </div>
                    <div className="bg-decision-warn/20 text-decision-warn p-6 rounded-lg border border-decision-warn/30">
                       <div className="font-bold text-3xl">{metrics?.confusion_matrix?.[0]?.[1]?.toLocaleString() || '0'}</div>
                       <div className="text-xs mt-1 opacity-80 uppercase">False Positive</div>
                    </div>
                    <div className="bg-decision-block/20 text-decision-block p-6 rounded-lg border border-decision-block/30">
                       <div className="font-bold text-3xl">{metrics?.confusion_matrix?.[1]?.[0]?.toLocaleString() || '0'}</div>
                       <div className="text-xs mt-1 opacity-80 uppercase">False Negative</div>
                    </div>
                    <div className="bg-decision-approve/20 text-decision-approve p-6 rounded-lg border border-decision-approve/30">
                       <div className="font-bold text-3xl">{metrics?.confusion_matrix?.[1]?.[1]?.toLocaleString() || '0'}</div>
                       <div className="text-xs mt-1 opacity-80 uppercase">True Positive</div>
                    </div>
                  </div>
               </div>
             </div>
           </div>
           
           <div className="grid grid-cols-4 gap-4">
             {['Precision', 'Recall', 'F1 Score', 'FPR'].map((m) => {
               let val = '0.0%';
               if (metrics?.xgboost) {
                 if (m === 'Precision') val = `${(metrics.xgboost.precision * 100).toFixed(1)}%`;
                 if (m === 'Recall') val = `${(metrics.xgboost.recall * 100).toFixed(1)}%`;
                 if (m === 'F1 Score') val = `${(metrics.xgboost.f1_score * 100).toFixed(1)}%`;
                 if (m === 'FPR') val = `${(metrics.fpr * 100).toFixed(1)}%`;
               }
               return (
                 <div key={m} className="card-finguard text-center py-6">
                   <div className="text-sm text-secondary tracking-wider uppercase mb-2">{m}</div>
                   <div className="text-3xl font-bold text-primary">{val}</div>
                 </div>
               );
             })}
           </div>
        </div>
      )}

      {tab === 'features' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
           <div className="card-finguard h-[500px]">
             <div className="flex justify-between items-center border-b border-border pb-3 mb-4">
               <h3 className="text-sm font-semibold">Global Feature Importance (SHAP Mean Absolute)</h3>
               <span className="text-xs text-muted flex items-center gap-1">
                 <Clock className="w-3 h-3" /> Last cached: {shap?.timestamp?.split('T')[1]?.split('.')[0] || 'N/A'}
               </span>
             </div>
             {!shap?.global_shap ? <div className="text-center text-muted pt-20">No SHAP data available</div> :
               <ResponsiveContainer width="100%" height="90%">
                 <BarChart data={Object.entries(shap.global_shap).map(([k,v]) => ({name: k, target: v})).sort((a,b) => b.target - a.target)} layout="vertical" margin={{left: 40}}>
                   <XAxis type="number" hide />
                   <YAxis type="category" dataKey="name" tick={{fill: '#8b949e', fontSize: 11}} width={120} />
                   <Tooltip cursor={{fill: '#21262d'}} contentStyle={{backgroundColor: '#161b22', borderColor: '#21262d'}} />
                   <Bar dataKey="target" fill="#bc8cff" radius={[0, 4, 4, 0]} />
                 </BarChart>
               </ResponsiveContainer>
             }
           </div>
        </div>
      )}

      {tab === 'drift' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
           <div className="flex justify-between items-center border-b border-border pb-4 bg-surface p-4 rounded-xl border">
              <div>
                 <h2 className="text-lg font-semibold flex items-center gap-2">
                   Data Drift Monitor
                   {drift?.status === 'drift_detected' && <span className="text-xs bg-decision-block text-white px-2 py-0.5 rounded-full">ACTION NEEDED</span>}
                 </h2>
                 <p className="text-xs text-secondary mt-1">
                   Live transaction distribution vs baseline validation set.
                   We run a KS test per feature; if `p-value &lt; 0.05`, the UI flags drift.
                 </p>
              </div>
              <button onClick={doDriftCheck} disabled={checking} className="bg-background border border-border hover:bg-surface text-primary px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors">
                 <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
                 {checking ? 'Analyzing Dist...' : 'Run Analysis'}
              </button>
           </div>
           
           <div className="grid grid-cols-3 gap-4">
             {drift?.drift_details ? Object.entries(drift.drift_details).map(([feat, data]) => (
               <div key={feat} className={`card-finguard border-l-4 ${data.drift_detected ? 'border-l-decision-block bg-decision-block/5' : 'border-l-decision-approve'}`}>
                 <div className="flex justify-between items-start mb-2">
                   <h3 className="font-medium text-sm text-primary max-w-[80%] truncate" title={feat}>{feat}</h3>
                   {data.drift_detected ? <AlertTriangle className="w-4 h-4 text-decision-block" /> : <CheckCircle className="w-4 h-4 text-decision-approve opacity-50" />}
                 </div>
                 <div className="text-xs text-secondary mb-1">KS Stat: <span className="font-mono text-primary">{data.ks_stat.toFixed(4)}</span></div>
                 <div className="text-xs text-secondary">P-value: <span className="font-mono text-primary">{data.p_value.toFixed(4)}</span></div>
               </div>
             )) : <div className="col-span-3 text-center text-muted py-8">No drift report available yet. Run Analysis.</div>}
           </div>
        </div>
      )}

      {tab === 'costs' && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
           <div className="card-finguard h-[400px]">
             <h3 className="text-sm font-semibold border-b border-border pb-2 mb-4">Financial Cost vs Friction Analysis</h3>
             <div className="flex justify-center items-center h-full text-secondary">
               <div className="text-center space-y-4">
                 {!metrics?.cost_analysis && (
                   <div className="text-xs text-muted border border-border bg-background px-3 py-2 rounded-lg max-w-md mx-auto">
                     Cost analysis is unavailable. Re-generate `models/metrics.json` (training scripts) or ensure the backend can read it.
                   </div>
                 )}
                 <div className="text-6xl text-decision-approve font-bold tracking-tighter">
                   {metrics?.cost_analysis?.fraud_prevented ? `₹${(metrics.cost_analysis.fraud_prevented / 1000000).toFixed(2)}M` : `₹0.0M`}
                 </div>
                 <div className="text-lg tracking-wide uppercase text-muted">Estimated Fraud Prevented</div>
                 <div className="text-sm mt-4 text-decision-warn">
                   {metrics?.cost_analysis?.false_positive_cost ? `₹${(metrics.cost_analysis.false_positive_cost / 1000).toFixed(1)}K` : `₹0.0K`} Lost to False Positive Friction
                 </div>
                 <p className="max-w-md mx-auto text-xs mt-6 opacity-60 leading-relaxed">Cost simulation leverages dynamic operational markers. Assumes ₹50 internal ops review per flagged true-negative transaction.</p>
               </div>
             </div>
           </div>
        </div>
      )}
    </div>
  );
}
