import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Analytics } from "./pages/Analytics";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ProjectDetail } from "./pages/ProjectDetail";
import { Register } from "./pages/Register";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { AuthProvider } from "./store/AuthContext";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/analytics" element={<Analytics />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
