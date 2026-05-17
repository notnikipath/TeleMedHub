import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 200,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<600"],
  },
};

export default function () {
  const response = http.get("http://localhost:8180/health");
  check(response, { "gateway health 200": (res) => res.status === 200 });
  sleep(0.2);
}
