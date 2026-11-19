import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import LandingPage from "./LandingPage";
import { GUEST_LOGIN } from "../test/mockAxios";

describe("LandingPage", () => {

  it("renders the hero and demo calls to action", () => {
    render(<MemoryRouter><LandingPage onLogin={vi.fn()} /></MemoryRouter>);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/catch pipeline problems/i);
    expect(screen.getAllByRole("button", { name: /try the demo/i }).length).toBeGreaterThan(0);
    for (const link of screen.getAllByRole("link", { name: /log in/i })) {
      expect(link).toHaveAttribute("href", "/login");
    }
  });

  it("starts a guest session from Try the demo", async () => {
    axios.post.mockResolvedValue({ data: GUEST_LOGIN });
    const onLogin = vi.fn();
    render(<MemoryRouter><LandingPage onLogin={onLogin} /></MemoryRouter>);

    await userEvent.click(screen.getAllByRole("button", { name: /try the demo/i })[0]);

    expect(axios.post).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/auth\/guest$/));
    expect(onLogin).toHaveBeenCalledWith("access-123", GUEST_LOGIN.user, "refresh-456");
  });
});
