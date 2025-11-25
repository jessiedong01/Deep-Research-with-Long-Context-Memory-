/**
 * Main App component with routing
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { RunsList } from './components/RunsList';
import { RunDetail } from './components/RunDetail';
import { NewRunForm } from './components/NewRunForm';
import { DAGTestPage } from './components/DAGTestPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <div className="header-content">
            <h1 className="logo">
              <a href="/">Research Pipeline Dashboard</a>
            </h1>
            <nav className="main-nav">
              <a href="/">Runs</a>
              <a href="/new">New Run</a>
              <a href="/test-dag">Test DAG</a>
            </nav>
          </div>
        </header>

        <main className="app-main">
          <Routes>
            <Route path="/" element={<RunsList />} />
            <Route path="/runs/:runId" element={<RunDetail />} />
            <Route path="/new" element={<NewRunForm />} />
            <Route path="/test-dag" element={<DAGTestPage />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <div className="footer-content">
            <p>Research Pipeline Dashboard v1.0.0</p>
            <p className="footer-note">
              All pipeline code lives in <code>src/</code> directory. 
              Dashboard can be removed with <code>rm -rf dashboard/</code>
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
