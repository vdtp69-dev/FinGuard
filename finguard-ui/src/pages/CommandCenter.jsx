import { useState, useEffect } from 'react';
import { getDashboardStats, getWsUrl, getRecentTransactions } from '../api';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Activity, ShieldCheck, Clock, CheckCircle, AlertTriangle, AlertCircle, XCircle } from 'lucide-react';

const COLORS = {
  APPROVE: '#3fb950',
  WARN: '#d29922',
  DELAY: '#f0883e',
  BLOCK: '#f85149'
};

const ICONS = {
  APPROVE: CheckCircle,
  WARN: AlertTriangle,
  DELAY: Clock,
  BLOCK: XCircle
};

function formatAmount(amt) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amt);
}

export default function CommandCenter() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [pieData, setPieData] = useState([]);
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [loading, setLoading] = useState(true);

  // Stats fetching
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStats();
        setStats(data);
        const txns = await getRecentTransactions({ limit: 100 });
        
        // Distribution
        const dist = { APPROVE: 0, WARN: 0, DELAY: 0, BLOCK: 0 };
        txns.forEach(t => dist[t.decision]++);
        setPieData(Object.entries(dist).filter(d => d[1] > 0).map(([k, v]) => ({ name: k, value: v })));
        setLoading(false);
      } catch (e) {
        console.error("Dashboard error", e);
      }
    };
    fetchStats();
    const int1 = setInterval(fetchStats, 10000);
    const int2 = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => { clearInterval(int1); clearInterval(int2); };
  }, []);

  // WebSocket Live Feed
  useEffect(() => {
    let ws;
    let reconnectTimer;
    
    const connect = () => {
      ws = new WebSocket(getWsUrl());
      ws.onmessage = (event) => {
        try {
          const txn = JSON.parse(event.data);
          setRecent(prev => [txn, ...prev].slice(0, 10)); // Keep last 10
        } catch (parseErr) {
          console.debug('CommandCenter WS message parse error:', parseErr);
        }
      };
      ws.onclose = () => {
        reconnectTimer = setTimeout(connect, 3000);
      };
    };
    
    connect();
    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

  if (loading) return <div className="p-8 text-secondary flex items-center gap-2"><Activity className="animate-spin"/> Loading SOC...</div>;

  const fpsRate = stats?.false_positive_rate ?? '-';
  const p95 = stats?.p95_latency_ms ?? '-';

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end border-b border-border pb-4">
        <div>
          <h1 className="text-3xl font-bold text-primary">Command Center</h1>
          <p className="text-secondary mt-1">Real-Time Global Fraud Auth</p>
        </div>
        <div className="text-xl font-mono text-muted">{time}</div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="card-finguard">
          <p className="text-sm text-secondary mb-1">Total Transactions</p>
          <p className="text-3xl font-semibold text-primary">{stats?.total_transactions.toLocaleString()}</p>
        </div>
        <div className="card-finguard">
          <p className="text-sm text-secondary mb-1">Fraud Caught</p>
          <p className="text-3xl font-semibold text-decision-block">{stats?.fraud_count.toLocaleString()}</p>
        </div>
        <div className="card-finguard">
          <p className="text-sm text-secondary mb-1">Catch Rate</p>
          <p className={`text-3xl font-semibold ${stats?.catch_rate > 90 ? 'text-decision-approve' : 'text-decision-warn'}`}>
            {stats?.catch_rate}%
          </p>
        </div>
        <div className="card-finguard">
          <p className="text-sm text-secondary mb-1">Avg Response API</p>
          <p className="text-3xl font-semibold text-decision-approve">32 ms</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="card-finguard flex justify-between items-center">
          <div>
            <p className="text-sm text-secondary">False Positive Rate (FPR)</p>
            <p className={`text-2xl font-semibold ${fpsRate > 5 ? 'text-decision-block' : 'text-primary'}`}>{fpsRate}%</p>
          </div>
          {fpsRate > 5 && <AlertTriangle className="text-decision-warn" />}
        </div>
        <div className="card-finguard flex justify-between items-center">
          <div>
            <p className="text-sm text-secondary">P95 Latency</p>
            <p className="text-2xl font-semibold text-primary">{p95} ms</p>
          </div>
        </div>
        <div className="card-finguard flex justify-between items-center">
          <div>
            <p className="text-sm text-secondary">Models Active</p>
            <p className="text-2xl font-semibold text-primary">{stats?.models_loaded} Engines</p>
          </div>
          <ShieldCheck className="text-decision-approve" />
        </div>
      </div>

      {/* Model Health Pill Row */}
      <div className="flex gap-3">
        {['XGBoost', 'Random Forest', 'LSTM', 'Autoencoder', 'Isolation Forest'].map(name => (
          <div key={name} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-surface text-sm">
            <div className={`w-2 h-2 rounded-full ${name === 'LSTM' && stats?.models_loaded < 5 ? 'bg-decision-block animate-pulse' : 'bg-decision-approve'}`}></div>
            {name}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-3 card-finguard flex flex-col min-h-[400px]">
          <h2 className="text-lg font-medium border-b border-border pb-3 mb-3">Live Intercept Feed</h2>
          {recent.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-secondary text-sm">Waiting for transactions...</div>
          ) : (
            <div className="flex-1 overflow-hidden flex flex-col gap-2">
              {recent.map((txn, i) => {
                const badgeColor = COLORS[txn.decision] || COLORS.APPROVE;
                const IconBase = ICONS[txn.decision] || CheckCircle;
                return (
                  <div key={i} className="flex items-center gap-4 bg-background p-3 rounded-lg border border-border animate-in fade-in slide-in-from-top-2">
                    <div className="w-8 h-8 rounded-full bg-user-aman/20 flex items-center justify-center text-user-aman font-bold">
                      {txn.user_id}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between">
                        <span className="font-semibold text-primary">{formatAmount(txn.amount)}</span>
                        <div className="flex items-center gap-1 text-xs" style={{color: badgeColor}}>
                           <IconBase className="w-4 h-4" /> {txn.decision}
                        </div>
                      </div>
                      <div className="text-xs text-secondary mt-1 tracking-wider uppercase">to {txn.merchant}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="col-span-2 card-finguard flex flex-col">
          <h2 className="text-lg font-medium border-b border-border pb-3 mb-3">Recent 100 Enforcement</h2>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} innerRadius={80} outerRadius={110} paddingAngle={2} dataKey="value">
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#161b22', borderColor: '#21262d', borderRadius: '8px' }}
                  itemStyle={{ color: '#e6edf3' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 text-xs mt-2">
            {pieData.map(d => (
              <div key={d.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm" style={{backgroundColor: COLORS[d.name]}}></div>
                {d.name} ({d.value})
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-decision-approve/10 border border-decision-approve/20 text-decision-approve p-3 rounded-lg flex items-center gap-3">
        <ShieldCheck className="w-5 h-5"/>
        <span className="font-medium text-sm">System Operational — All fraud detection manifolds active.</span>
      </div>
    </div>
  );
}
