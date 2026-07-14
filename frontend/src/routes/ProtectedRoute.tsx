import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../store/AuthContext";

export function ProtectedRoute() {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
