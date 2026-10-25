import { useState } from "react";
import { api, setToken } from "./api.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    try {
      const res = await api("/auth/login", { method: "POST", body: { username, password } });
      setToken(res.access_token);
      onLogin(res.user);
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="login">
      <h1>SupportOps</h1>
      <p className="muted">Sign in to create and follow support tickets.</p>
      <form onSubmit={submit}>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit">Sign in</button>
      </form>
      <p className="muted small">Demo accounts: admin, tech1, tech2, user1, user2 (password: username + 123).</p>
    </div>
  );
}
