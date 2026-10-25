let token = localStorage.getItem("token");

export const setToken = (t) => {
  token = t;
  t ? localStorage.setItem("token", t) : localStorage.removeItem("token");
};
export const hasToken = () => !!token;

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && token) {
    setToken(null);
    window.location.reload();
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const d = data?.detail;
    throw new Error(typeof d === "string" ? d : "Request failed");
  }
  return data;
}

export const STATUS_LABEL = {
  open: "Open", in_progress: "In progress", resolved: "Resolved", closed: "Closed",
};
export const isStaff = (u) => u && (u.role === "technician" || u.role === "admin");
export const isLate = (t) =>
  t.due_at && !["resolved", "closed"].includes(t.status) && new Date(t.due_at) < new Date();
