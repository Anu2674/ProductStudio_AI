import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../store/AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("redirects to login when there is no token", () => {
    localStorage.removeItem("access_token");
    renderProtected();
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders the protected content when a token exists", () => {
    localStorage.setItem("access_token", "fake-token");
    renderProtected();
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });
});
