import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, Car, Clock, Eye,
  FileVideo, Gauge, History, LayoutDashboard, PlayCircle, ShieldCheck,
  Upload, Users
} from 'lucide-react';

const API = 'http://127.0.0.1:8000';
const Card = ({ children, className = '' }) => <div className={`card ${className}`}>{children}</div>;

const navItems = [
  ['dashboard', 'Dashboard', LayoutDashboard],
  ['analysis', 'Video Analysis', FileVideo],
  ['events', 'Risk Events', AlertTriangle],
  ['history', 'Analysis History', History],
];

function App() {
  const [view, setView] = useState('dashboard');
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [apiReady, setApiReady] = useState(false);

  const loadRuns = async () => {
    try {
      const r = await fetch(`${API}/api/v1/runs`);
      if (r.ok) setRuns(await r.json());
    } catch (_) {}
  };

  const checkApi = async () => {
    try {
      const r = await fetch(`${API}/health`);
      setApiReady(r.ok);
    } catch (_) {
      setApiReady(false);
    }
  };

  useEffect(() => {
    loadRuns();
    checkApi();
  }, []);

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(`${API}/api/v1/analyze/video`, { method: 'POST', body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Analysis failed');
      setResult(data);
      await loadRuns();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const summary = result?.summary || {};
  const counts = result?.detected_by_class || {};
  const maxClassCount = Math.max(1, ...Object.values(counts));
  const latestRun = runs[0];

  const pageMeta = useMemo(() => ({
    dashboard: ['Road Safety Dashboard', 'A concise overview of traffic-safety intelligence and recent analysis activity.'],
    analysis: ['Video Analysis', 'Upload traffic footage and inspect the complete computer-vision analysis.'],
    events: ['Risk Events', 'Review confirmed near-miss interactions, TTC and closest-point-of-approach evidence.'],
    history: ['Analysis History', 'Review previous RoadWatch AI processing runs and risk scores.'],
  }[view]), [view]);

  const go = (next) => setView(next);

  return (
    <div className="app">
      <aside>
        <div className="brand">
          <div className="logo"><Eye size={22} /></div>
          <div><b>RoadWatch AI</b><small>Traffic Safety Intelligence</small></div>
        </div>
        <nav>
          {navItems.map(([key, label, Icon]) => (
            <button key={key} className={view === key ? 'active' : ''} onClick={() => go(key)}>
              <Icon />{label}
            </button>
          ))}
        </nav>
        <div className="sidefoot"><ShieldCheck /><span>Computer Vision<br /><small>Near-Miss Analytics</small></span></div>
      </aside>

      <main>
        <header>
          <div>
            <p className="eyebrow">TRAFFIC INTELLIGENCE PLATFORM</p>
            <h1>{pageMeta[0]}</h1>
            <p>{pageMeta[1]}</p>
          </div>
          <div className={`status ${apiReady ? '' : 'offline'}`}><i />{apiReady ? 'API READY' : 'API OFFLINE'}</div>
        </header>

        {view === 'dashboard' && (
          <>
            <section className="welcomeGrid">
              <Card className="welcome">
                <div className="welcomeIcon"><Activity /></div>
                <div>
                  <p className="eyebrow">ROADWATCH INTELLIGENCE</p>
                  <h2>From traffic footage to explainable safety signals.</h2>
                  <p>YOLO detection, ByteTrack tracking, trajectory motion, TTC/CPA analysis and temporal near-miss confirmation in one workflow.</p>
                  <button className="primary compact" onClick={() => go('analysis')}>Analyze a video <ArrowRight size={16} /></button>
                </div>
              </Card>
              <Card className="snapshot">
                <div className="sectionTitle"><span><BarChart3 />Latest Snapshot</span></div>
                <div className="snapshotRows">
                  <div><span>Completed analyses</span><strong>{runs.filter(r => r.status === 'completed').length}</strong></div>
                  <div><span>Latest risk score</span><strong>{latestRun ? Number(latestRun.risk_score || 0).toFixed(1) : '—'}</strong></div>
                  <div><span>Latest events</span><strong>{latestRun?.total_events ?? '—'}</strong></div>
                </div>
              </Card>
            </section>

            <section className="featureGrid">
              <Card><Eye /><b>Road-User Detection</b><span>Pedestrians, bicycles, motorcycles, cars, buses and trucks.</span></Card>
              <Card><Users /><b>Multi-Object Tracking</b><span>Persistent track identities and short trajectory histories.</span></Card>
              <Card><Gauge /><b>TTC + CPA Risk</b><span>Relative-motion indicators for approaching road-user pairs.</span></Card>
              <Card><AlertTriangle /><b>Near-Miss Confirmation</b><span>Temporal validation reduces isolated one-frame risk alerts.</span></Card>
            </section>

            <Card className="history previewHistory">
              <div className="sectionTitle"><span><History />Recent Analyses</span><button className="textButton" onClick={() => go('history')}>View all <ArrowRight size={14} /></button></div>
              <RunTable runs={runs.slice(0, 5)} />
            </Card>
          </>
        )}

        {view === 'analysis' && (
          <>
            <section className="grid hero">
              <Card className="upload">
                <div className="sectionTitle"><span><Upload />Analyze Traffic Video</span><small>YOLO + ByteTrack + TTC/CPA</small></div>
                <label className="drop">
                  <FileVideo size={38} />
                  <b>{file ? file.name : 'Drop or select a traffic video'}</b>
                  <span>MP4, AVI, MOV or MKV</span>
                  <input type="file" accept="video/*" onChange={e => setFile(e.target.files?.[0] || null)} />
                  <em>Choose video</em>
                </label>
                <button className="primary" disabled={!file || loading} onClick={analyze}>{loading ? 'Analyzing video…' : 'Run Risk Analysis'}</button>
                {loading && <><div className="progress"><span /></div><p className="processingNote">Detecting road users, tracking motion and evaluating interactions. Keep this page open.</p></>}
                {error && <p className="error">{error}</p>}
              </Card>

              <Card className="overview">
                <div className="sectionTitle"><span><Activity />Analysis Overview</span></div>
                {result ? <>
                  <div className={`risk ${String(summary.overall_risk_level || 'low').toLowerCase()}`}>
                    <small>OVERALL RISK</small><strong>{summary.overall_risk_score}</strong><b>{summary.overall_risk_level}</b>
                  </div>
                  <div className="mini">
                    <div><Clock /><b>{result.processing_time_seconds}s</b><span>Processing</span></div>
                    <div><Users /><b>{result.unique_road_users}</b><span>Road users</span></div>
                    <div><AlertTriangle /><b>{summary.total_near_miss_events}</b><span>Near misses</span></div>
                  </div>
                </> : <div className="empty"><Activity size={38} /><b>No analysis yet</b><span>Choose a traffic video to generate safety intelligence.</span></div>}
              </Card>
            </section>

            {result && <>
              <section className="stats">
                <Card><Car /><span>Tracked Road Users</span><strong>{result.unique_road_users}</strong></Card>
                <Card><AlertTriangle /><span>High Risk Events</span><strong>{summary.high_risk_events}</strong></Card>
                <Card><ShieldCheck /><span>Critical Events</span><strong>{summary.critical_events}</strong></Card>
                <Card><Activity /><span>Analysis FPS</span><strong>{result.analysis_fps}</strong></Card>
              </section>

              <section className="grid detail">
                <Card>
                  <div className="sectionTitle"><span><Eye />Detected Road Users</span></div>
                  <div className="classes">
                    {Object.entries(counts).map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b><div><i style={{ width: `${Math.max(8, v / maxClassCount * 100)}%` }} /></div></div>)}
                  </div>
                </Card>
                <Card>
                  <div className="sectionTitle"><span><AlertTriangle />Near-Miss Summary</span><button className="textButton" onClick={() => go('events')}>Open events <ArrowRight size={14} /></button></div>
                  {result.events.length ? <div className="events">{result.events.slice(0, 3).map((e, i) => <EventRow key={i} event={e} />)}</div> : <div className="empty small">No confirmed high-risk interactions.</div>}
                </Card>
              </section>

              <Card className="videoCard">
                <div className="sectionTitle"><span><PlayCircle />Annotated Analysis</span><small>Tracked road users and confirmed interactions</small></div>
                <video controls src={`${API}${result.output_video_url}`} />
              </Card>
            </>}
          </>
        )}

        {view === 'events' && (
          <Card className="eventsPage">
            <div className="sectionTitle"><span><AlertTriangle />Confirmed Near-Miss Events</span><small>{result ? `${result.events.length} in current analysis` : 'Run an analysis first'}</small></div>
            {result?.events?.length ? <div className="events expanded">{result.events.map((e, i) => <EventRow key={i} event={e} expanded />)}</div> : <div className="empty pageEmpty"><AlertTriangle size={42} /><b>No current risk events</b><span>Run a video analysis first. Confirmed HIGH and CRITICAL interactions will appear here with TTC and CPA evidence.</span><button className="primary compact" onClick={() => go('analysis')}>Go to Video Analysis <ArrowRight size={15} /></button></div>}
          </Card>
        )}

        {view === 'history' && (
          <Card className="history historyPage">
            <div className="sectionTitle"><span><History />Analysis History</span><small>{runs.length} runs</small></div>
            <RunTable runs={runs} />
          </Card>
        )}

        <footer>RoadWatch AI · Traffic Near-Miss Detection & Risk Analysis</footer>
      </main>
    </div>
  );
}

function EventRow({ event, expanded = false }) {
  return <div className={`event ${expanded ? 'expandedRow' : ''}`}>
    <b className={String(event.risk_level).toLowerCase()}>{event.risk_level}</b>
    <div><strong>{event.object_a} ↔ {event.object_b}</strong><span>At {event.timestamp_seconds}s · Risk score {event.risk_score}</span></div>
    <div><small>TTC</small><strong>{event.estimated_ttc ?? '—'}s</strong></div>
    <div><small>CPA</small><strong>{event.closest_approach_px ?? '—'}px</strong></div>
    {expanded && <div><small>Approaching</small><strong>{event.approaching ? 'Yes' : 'No'}</strong></div>}
  </div>;
}

function RunTable({ runs }) {
  return <div className="table">
    <div className="tr head"><span>Video</span><span>Status</span><span>Events</span><span>Risk Score</span></div>
    {runs.length ? runs.map(r => <div className="tr" key={r.id}><span><FileVideo size={16} />{r.filename}</span><span className={r.status === 'completed' ? 'success' : 'muted'}>{r.status}</span><span>{r.total_events}</span><span>{Number(r.risk_score || 0).toFixed(1)}</span></div>) : <div className="empty small">No analysis history yet.</div>}
  </div>;
}

export default App;
