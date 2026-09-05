import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import HealthCheck from "./HealthCheck.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders backend status after fetching /api/health", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ status: "ok" }),
      }),
    ),
  );

  render(<HealthCheck />);

  expect(await screen.findByText("Backend health: ok")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(
    "/api/health",
    expect.objectContaining({ signal: expect.anything() }),
  );
});

test("renders error when the fetch fails or times out", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.reject(
        new DOMException("The operation was aborted.", "AbortError"),
      ),
    ),
  );

  render(<HealthCheck />);

  expect(await screen.findByText("Backend health: error")).toBeInTheDocument();
});
