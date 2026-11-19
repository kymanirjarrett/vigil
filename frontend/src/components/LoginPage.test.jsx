import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import LoginPage from "./LoginPage";
import { GUEST_LOGIN } from "../test/mockAxios";

const renderPage = (onLogin = vi.fn()) =>
  render(<MemoryRouter><LoginPage onLogin={onLogin} /></MemoryRouter>);

describe("LoginPage", () => {

  it("renders the sign-in form and the Try the demo button", () => {
    renderPage();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try the demo/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign up/i })).toHaveAttribute("href", "/signup");
  });

  it("Try the demo logs in as the guest", async () => {
    axios.post.mockResolvedValue({ data: GUEST_LOGIN });
    const onLogin = vi.fn();
    renderPage(onLogin);

    await userEvent.click(screen.getByRole("button", { name: /try the demo/i }));

    expect(onLogin).toHaveBeenCalledWith("access-123", GUEST_LOGIN.user, "refresh-456");
  });

  it("explains a rate-limited demo request", async () => {
    axios.post.mockRejectedValue({ response: { status: 429 } });
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: /try the demo/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/too many demo sessions/i);
  });
});
