import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { LeadsPage } from "./pages/Leads";
import { LoginPage } from "./pages/Login";
import { SettingsPage } from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/leads"
        element={
          <ProtectedRoute>
            <LeadsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/leads" replace />} />
      <Route path="*" element={<Navigate to="/leads" replace />} />
    </Routes>
  );
}
