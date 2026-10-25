import { useCallback, useEffect, useState } from "react";
import { api, isLate, isStaff, STATUS_LABEL } from "./api.js";

const NEXT = { open: ["in_progress"], in_progress: ["resolved", "open"], resolved: ["closed", "open"], closed: [] };
const ACTION = { in_progress: "Start work", resolved: "Mark resolved", closed: "Close ticket", open: "Reopen" };

function describe(e) {
  const who = e.actor?.full_name ?? "System";
  if (e.type === "created") return `${who} created the ticket`;
  if (e.type === "status_changed") return `${who} changed status: ${STATUS_LABEL[e.old_value]} → ${STATUS_LABEL[e.new_value]}`;
  if (e.type === "assigned") return `${who} assigned to ${e.new_value ?? "nobody"}${e.old_value ? ` (was ${e.old_value})` : ""}`;
  if (e.type === "field_changed") return `${who} changed ${e.field}: ${e.old_value ?? "empty"} → ${e.new_value ?? "empty"}`;
  return `${who} commented`;
}

export default function TicketDetail({ id, user, onBack }) {
  const [t, setT] = useState(null);
  const [techs, setTechs] = useState([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const staff = isStaff(user);

  const load = useCallback(() => api(`/tickets/${id}`).then(setT).catch((e) => setError(e.message)), [id]);
  useEffect(() => { load(); if (staff) api("/users/technicians").then(setTechs); }, [load, staff]);

  const run = (fn) => async () => { setError(""); try { await fn(); await load(); } catch (e) { setError(e.message); } };
  const changeStatus = (s) => run(() => api(`/tickets/${id}/status`, { method: "POST", body: { status: s } }));
  const assign = (v) => run(() => api(`/tickets/${id}/assign`, { method: "POST", body: { technician_id: v ? Number(v) : null } }))();
  const send = (e) => {
    e.preventDefault();
    run(async () => { await api(`/tickets/${id}/comments`, { method: "POST", body: { body: comment } }); setComment(""); })();
  };

  if (!t) return <p>{error || "Loading…"}</p>;
  const actions = NEXT[t.status].filter((s) => staff || (t.status === "resolved" && s === "open"));

  return (
    <article className="detail">
      <button className="quiet" onClick={onBack}>Back to tickets</button>
      <div className="panel">
        <h2>#{t.id} {t.title}</h2>
        <p className="meta">
          <span className={`tag s-${t.status}`}>{STATUS_LABEL[t.status]}</span>{" "}
          <span className={`tag p-${t.priority}`}>{t.priority}</span> · {t.category} · from {t.source} ·
          created by {t.creator?.full_name ?? "system"} on {new Date(t.created_at).toLocaleString()}
          {t.due_at && <span className={isLate(t) ? "late" : ""}> · due {new Date(t.due_at).toLocaleDateString()}</span>}
        </p>
        <p className="desc">{t.description || <span className="muted">No description.</span>}</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          {actions.map((s) => <button key={s} onClick={changeStatus(s)}>{ACTION[s]}</button>)}
          {staff && (
            <label className="inline">Technician
              <select value={t.technician?.id ?? ""} onChange={(e) => assign(e.target.value)}>
                <option value="">Unassigned</option>
                {techs.filter((x) => user.role === "admin" || x.id === user.id).map((x) => <option key={x.id} value={x.id}>{x.full_name}</option>)}
              </select>
            </label>
          )}
        </div>
      </div>

      <div className="cols">
        <section className="panel">
          <h3>Comments</h3>
          {t.comments.length === 0 && <p className="muted">No comments yet.</p>}
          {t.comments.map((c) => (
            <div key={c.id} className="comment">
              <strong>{c.author?.full_name ?? "System"}</strong> <span className="muted small">{new Date(c.created_at).toLocaleString()}</span>
              <p>{c.body}</p>
            </div>
          ))}
          {t.status !== "closed" && (
            <form onSubmit={send}>
              <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Write a comment" required />
              <button type="submit">Add comment</button>
            </form>
          )}
        </section>
        <section className="panel">
          <h3>History</h3>
          <ul className="history">
            {t.events.map((e) => (
              <li key={e.id}>{describe(e)}<br /><span className="muted small">{new Date(e.created_at).toLocaleString()}</span></li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  );
}
