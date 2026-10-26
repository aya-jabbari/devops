import { useEffect, useState } from "react";
import { api, isLate, isStaff, STATUS_LABEL } from "./api.js";

export default function TicketList({ user, onOpen, initial = {} }) {
  const [tickets, setTickets] = useState([]);
  const [techs, setTechs] = useState([]);
  const [f, setF] = useState({ q: "", status: "", priority: "", source: "", technician_id: "", late: "", ...initial });
  const [error, setError] = useState("");
  const staff = isStaff(user);

  useEffect(() => { if (staff) api("/users/technicians").then(setTechs).catch(() => {}); }, [staff]);

  useEffect(() => {
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
    const timer = setTimeout(() => {
      api(`/tickets${qs ? `?${qs}` : ""}`).then(setTickets).catch((e) => setError(e.message));
    }, 200);
    return () => clearTimeout(timer);
  }, [f]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <section>
      <h2>{staff ? "All tickets" : "My tickets"}</h2>
      <div className="filters">
        <input placeholder="Search by #id or title" value={f.q} onChange={set("q")} aria-label="Search" />
        <select value={f.status} onChange={set("status")} aria-label="Status">
          <option value="">Any status</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={f.priority} onChange={set("priority")} aria-label="Priority">
          <option value="">Any priority</option>
          {["low", "medium", "high", "critical"].map((p) => <option key={p}>{p}</option>)}
        </select>
        {staff && (
          <>
            <label className="inline"><input type="checkbox" checked={f.late === "true"}
              onChange={(e) => setF({ ...f, late: e.target.checked ? "true" : "" })} /> Late only</label>
            <select value={f.source} onChange={set("source")} aria-label="Source">
              <option value="">Any source</option><option value="user">User</option><option value="monitoring">Monitoring</option>
            </select>
            <select value={f.technician_id} onChange={set("technician_id")} aria-label="Technician">
              <option value="">Any technician</option>
              {techs.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
            </select>
          </>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {tickets.length === 0 ? (
        <p className="muted">No tickets match. Create one with “New ticket”.</p>
      ) : (
        <table>
          <thead><tr><th>#</th><th>Title</th><th>Status</th><th>Priority</th><th>Technician</th><th>Due</th></tr></thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id} onClick={() => onOpen(t.id)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(t.id)}>
                <td>{t.id}</td>
                <td>{t.title}</td>
                <td><span className={`tag s-${t.status}`}>{STATUS_LABEL[t.status]}</span></td>
                <td><span className={`tag p-${t.priority}`}>{t.priority}</span></td>
                <td>{t.technician?.full_name ?? "Unassigned"}</td>
                <td className={isLate(t) ? "late" : ""}>{t.due_at ? new Date(t.due_at).toLocaleDateString() : "—"}{isLate(t) && " (late)"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
