import { useState } from "react";
import { api } from "./api.js";

export default function NewTicket({ onCreated, onCancel }) {
  const [f, setF] = useState({ title: "", description: "", category: "general", priority: "medium", due_at: "" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    try {
      const body = { ...f, due_at: f.due_at ? new Date(f.due_at).toISOString() : null };
      onCreated(await api("/tickets", { method: "POST", body }));
    } catch (err) { setError(err.message); }
  }

  return (
    <form className="panel form" onSubmit={submit}>
      <h2>New ticket</h2>
      <label>Title<input value={f.title} onChange={set("title")} minLength={3} required /></label>
      <label>Description<textarea rows={5} value={f.description} onChange={set("description")} /></label>
      <div className="row">
        <label>Category
          <select value={f.category} onChange={set("category")}>
            {["general", "network", "hardware", "software", "access"].map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Priority
          <select value={f.priority} onChange={set("priority")}>
            {["low", "medium", "high", "critical"].map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Due date<input type="date" value={f.due_at} onChange={set("due_at")} /></label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button type="submit">Create ticket</button>
        <button type="button" className="quiet" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
