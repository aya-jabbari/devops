import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const USERNAME = __ENV.K6_USERNAME || "user1";
const PASSWORD = __ENV.K6_PASSWORD || "user1123";

// Sustained traffic during Argo Rollouts canary pause so Prometheus [2m] 5xx rate has enough samples.
export const options = {
  scenarios: {
    canary_load: {
      executor: "constant-vus",
      vus: Number(__ENV.K6_VUS || 20),
      duration: __ENV.K6_DURATION || "90s",
    },
  },
  thresholds: {
    // Matches the 2% 5xx abort threshold defined in docs/interfaces.md and Argo Rollouts AnalysisTemplate.
    http_req_failed: ["rate<0.02"],
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
  };

  const readyRes = http.get(`${BASE_URL}/readyz`);
  check(readyRes, {
    "readyz is 200": (r) => r.status === 200,
  });

  const ticketsRes = http.get(`${BASE_URL}/api/tickets`, {
    headers: authHeaders,
  });
  check(ticketsRes, {
    "tickets is 200": (r) => r.status === 200,
  });

  sleep(0.3);
}
