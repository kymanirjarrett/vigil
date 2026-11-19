import { vi } from "vitest";
import seed from "./fixtures/seed-api.json";

// Real responses captured from the backend running DATA_SOURCE=seed.
export const seedResponses = seed;

export function axiosMock() {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      defaults: { headers: { common: {} } },
      interceptors: { response: { use: vi.fn(), eject: vi.fn() } },
    },
  };
}

/** Answer GETs from the seed fixtures by path; unknown paths reject. */
export function serveSeed(axios) {
  axios.get.mockImplementation((url) => {
    const path = new URL(url).pathname;
    return path in seed
      ? Promise.resolve({ data: seed[path] })
      : Promise.reject(new Error(`unmocked GET ${path}`));
  });
}

export const GUEST_LOGIN = {
  access_token: "access-123",
  refresh_token: "refresh-456",
  user: { id: "u1", email: "guest@demo.invalid", role: "guest" },
};
