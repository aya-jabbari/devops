import { useEffect, useState } from "react";
import { api, hasToken, setToken } from "./api.js";
import Login from "./Login.jsx";
import TicketList from "./TicketList.jsx";
import TicketDetail from "./TicketDetail.jsx";
import NewTicket from "./NewTicket.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());
  const [view, setView] = useState({ name: "list" }); // list | new | ticket(id)

  useEffect(() => {
    if (hasToken()) api("/auth/me").then(setUser).catch(() => {}).finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return <Login onLogin={setUser} />;

  const logout = () => { setToken(null); setUser(null); setView({ name: "list" }); };

  return (
    <>
      <header className="bar">
        <button className="brand" onClick={() => setView({ name: "list" })}>SupportOps</button>
        <nav>
          <button onClick={() => setView({ name: "new" })}>New ticket</button>
          <span className="who">{user.full_name} ({user.role})</span>
          <button className="quiet" onClick={logout}>Sign out</button>
        </nav>
      </header>
      <main>
        {view.name === "list" && <TicketList user={user} onOpen={(id) => setView({ name: "ticket", id })} />}
        {view.name === "new" && (
          <NewTicket onCreated={(t) => setView({ name: "ticket", id: t.id })} onCancel={() => setView({ name: "list" })} />
        )}
        {view.name === "ticket" && (
          <TicketDetail id={view.id} user={user} onBack={() => setView({ name: "list" })} />
        )}
      </main>
    </>
  );
}
