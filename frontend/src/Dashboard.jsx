import { useEffect, useState } from "react";
import { api } from "./api.js";

function Tile({ label, value, tone, onClick }) {
  return (
    <button className={`tile ${tone ?? ""}`} onClick={onClick} disabled={!onClick}>
      <span className="tile-value">{value}</span>
      <span className="tile-label">{label}</span>
    </button>
  );
}

export default function Dashboard({ onOpenList }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api("/dashboard").then(setD).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!d) return <p>Loading…</p>;

  const maxPriority = Math.max(1, ...Object.values(d.priorities));
  const maxLoad = Math.max(1, ...d.workload.map((w) => w.active));

  return (
    <section>
      <h2>Dashboard</h2>
      <div className="tiles">
        <Tile label="Open" value={d.open} onClick={() => onOpenList({ status: "open" })} />
        <Tile label="In progress" value={d.in_progress} onClick={() => onOpenList({ status: "in_progress" })} />
        <Tile label="Late" value={d.late} tone={d.late ? "bad" : ""} onClick={() => onOpenList({ late: "true" })} />
        <Tile label="Unassigned" value={d.unassigned} tone={d.unassigned ? "warn" : ""} />
        <Tile label="Active incidents" value={d.incidents} onClick={() => onOpenList({ source: "monitoring" })} />
      </div>

      <div className="cols">
        <section className="panel">
          <h3>Active tickets by priority</h3>
          {Object.entries(d.priorities).map(([p, n]) => (
            <div key={p} className="bar-row">
              <span className={`tag p-${p}`}>{p}</span>
              <span className="meter"><span className={`fill p-${p}`} style={{ width: `${(n / maxPriority) * 100}%` }} /></span>
              <button className="link" onClick={() => onOpenList({ priority: p })}>{n}</button>
            </div>
          ))}
        </section>

        <section className="panel">
          <h3>Workload per technician</h3>
          {d.workload.length === 0 && <p className="muted">No technicians.</p>}
          {d.workload.map((w) => (
            <div key={w.technician_id} className="bar-row">
              <span>{w.name}</span>
              <span className="meter"><span className="fill" style={{ width: `${(w.active / maxLoad) * 100}%` }} /></span>
              <button className="link" onClick={() => onOpenList({ technician_id: String(w.technician_id) })}>
                {w.active}{w.late > 0 && <span className="late"> ({w.late} late)</span>}
              </button>
            </div>
          ))}
        </section>
      </div>
    </section>
  );
}
