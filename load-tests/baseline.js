import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const USERNAME = __ENV.K6_USERNAME || "user1";
const PASSWORD = __ENV.K6_PASSWORD || "user1123";

export const options = {
  stages: [
    { duration: "15s", target: 5 },
    { duration: "30s", target: 10 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(res, {
    "login status is 200": (r) => r.status === 200,
    "login returned access_token": (r) => Boolean(r.json("access_token")),
  });

  return { token: res.json("access_token") };
}

export default function (data) {
  const authHeaders = {
    Authorization: `Bearer ${data.token}`,
    "Content-Type": "application/json",
  };

  const healthRes = http.get(`${BASE_URL}/healthz`);
  check(healthRes, {
    "healthz is 200": (r) => r.status === 200,
  });

  const listRes = http.get(`${BASE_URL}/api/tickets`, { headers: authHeaders });
  check(listRes, {
    "list tickets is 200": (r) => r.status === 200,
  });

  const createPayload = JSON.stringify({
    title: `k6 baseline ticket VU-${__VU}-${__ITER}`,
    description: "Ticket genere par le test de charge nominal k6.",
    category: "network",
    priority: "medium",
  });

  const createRes = http.post(`${BASE_URL}/api/tickets`, createPayload, {
    headers: authHeaders,
  });
  check(createRes, {
    "create ticket is 201": (r) => r.status === 201,
  });

  sleep(1);
}
