import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import './index.css';

import App from './App.jsx';
import CommandCenter from './pages/CommandCenter.jsx';
import ScoreTransaction from './pages/ScoreTransaction.jsx';
import LiveFeed from './pages/LiveFeed.jsx';
import ModelIntelligence from './pages/ModelIntelligence.jsx';
import NetworkGraph from './pages/NetworkGraph.jsx';
import AdversarialProbe from './pages/AdversarialProbe.jsx';
import Federated from './pages/Federated.jsx';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <CommandCenter /> },
      { path: 'score', element: <ScoreTransaction /> },
      { path: 'live', element: <LiveFeed /> },
      { path: 'intelligence', element: <ModelIntelligence /> },
      { path: 'network', element: <NetworkGraph /> },
      { path: 'probe', element: <AdversarialProbe /> },
      { path: 'federated', element: <Federated /> }
    ]
  }
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
