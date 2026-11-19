import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// No test talks to a real server: axios is a mock everywhere.
vi.mock("axios", async () => (await import("./mockAxios")).axiosMock());

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});
