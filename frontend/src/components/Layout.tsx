import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../store/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <nav className="navbar">
        <Link to="/dashboard" className="navbar-brand">
          <span className="navbar-brand-mark">PS</span>
          ProductStudio AI
        </Link>
        <div className="navbar-links">
          <Link to="/dashboard">Projects</Link>
          <button className="secondary" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </nav>
      <div className="page">{children}</div>
    </div>
  );
}
