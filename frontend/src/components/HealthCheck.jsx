import { useEffect, useState } from "react";

function HealthCheck() {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    fetch("/api/health", { signal: AbortSignal.timeout(2000) })
      .then((res) => res.json())
      .then((data) => setStatus(data.status === "ok" ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  return <p>Backend health: {status}</p>;
}

export default HealthCheck;
