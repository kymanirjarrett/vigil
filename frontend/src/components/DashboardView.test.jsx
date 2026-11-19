import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import AppShell from "./AppShell";
import DashboardView from "./DashboardView";
import { serveSeed, seedResponses, GUEST_LOGIN } from "../test/mockAxios";

describe("Dashboard on seeded data", () => {
  it("lists every seed job and flags sample data", async () => {
    serveSeed(axios);
    render(
      <MemoryRouter initialEntries={["/app/dashboard"]}>
        <Routes>
          <Route path="/app" element={<AppShell user={GUEST_LOGIN.user} onLogout={vi.fn()} />}>
            <Route path="dashboard" element={<DashboardView />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const jobs = seedResponses["/api/v1/glue/jobs"].jobs;
    expect(await screen.findByText(`Glue Jobs — ${jobs.length} found`)).toBeInTheDocument();
    const table = screen.getByText(`Glue Jobs — ${jobs.length} found`).closest(".panel");
    for (const job of jobs) {
      expect(within(table).getByText(job.name)).toBeInTheDocument();
    }
    expect(await screen.findByText("Sample data")).toBeInTheDocument();
  });
});
