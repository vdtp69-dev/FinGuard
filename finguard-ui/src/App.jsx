import { Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';

export default function App() {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <div className="mx-auto w-full max-w-7xl animate-in fade-in slide-in-from-bottom-2 duration-500 ease-out">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
