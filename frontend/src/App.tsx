import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { BriefPage } from "./pages/BriefPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { NewBriefPage } from "./pages/NewBriefPage";
import { RegisterPage } from "./pages/RegisterPage";

function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          ResearchAI
        </Link>
        <nav>
          <Link to="/">New Brief</Link>
          <Link to="/history">History</Link>
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
        <Route path="/" element={<NewBriefPage />} />
        <Route path="/briefs/:id" element={<BriefPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
