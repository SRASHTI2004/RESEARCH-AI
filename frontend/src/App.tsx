import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";

// Signed-in pages are split out so the landing/login page loads fast;
// AppShell wraps them in a Suspense boundary.
const JobsPage = lazy(() => import("./pages/JobsPage").then((m) => ({ default: m.JobsPage })));
const JobDetailPage = lazy(() => import("./pages/JobDetailPage").then((m) => ({ default: m.JobDetailPage })));
const TrackerPage = lazy(() => import("./pages/TrackerPage").then((m) => ({ default: m.TrackerPage })));
const NewBriefPage = lazy(() => import("./pages/NewBriefPage").then((m) => ({ default: m.NewBriefPage })));
const BriefPage = lazy(() => import("./pages/BriefPage").then((m) => ({ default: m.BriefPage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then((m) => ({ default: m.HistoryPage })));

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
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
