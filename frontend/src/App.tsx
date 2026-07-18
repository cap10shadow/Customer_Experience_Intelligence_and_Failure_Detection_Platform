import './App.css'

function App() {
  return (
    <div className="dashboard">
      <header className="header">
        <h1>Operational Intelligence Platform</h1>
      </header>
      <main className="content">
        <h2>Dashboard</h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <h3>Total Complaints</h3>
            <p className="metric-value">1,245</p>
          </div>
          <div className="metric-card">
            <h3>Anomalies Detected</h3>
            <p className="metric-value">12</p>
          </div>
          <div className="metric-card">
            <h3>System Status</h3>
            <p className="metric-value status-ok">Healthy</p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
