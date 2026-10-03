import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { BriefPage } from "./pages/BriefPage";
import { HistoryPage } from "./pages/HistoryPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewBriefPage } from "./pages/NewBriefPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TrackerPage } from "./pages/TrackerPage";

function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          Job Assistant
        </Link>
        <nav>
          <Link to="/jobs">Jobs</Link>
          <Link to="/tracker">Tracker</Link>
          <Link to="/briefs/new">New Brief</Link>
          <Link to="/history">Briefs</Link>
        </nav>
        {user && (
          <div className="user-menu">
            <span>{user.email}</span>
            <button type="button" onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/jobs" replace />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:id" element={<JobDetailPage />} />
        <Route path="/tracker" element={<TrackerPage />} />
        <Route path="/briefs/new" element={<NewBriefPage />} />
        <Route path="/briefs/:id" element={<BriefPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
