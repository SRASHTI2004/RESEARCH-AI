import { Briefcase, FileText, Info, KanbanSquare, Menu, Sparkles, X, type LucideIcon } from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ListSkeleton } from "@/components/states";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/auth/useAuth";
import { usePublicConfig } from "@/lib/publicConfig";
import { cn } from "@/lib/utils";
import { Brand } from "./Brand";
import { CompactUserMenu, SidebarUserMenu } from "./UserMenu";

const NAV: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/tracker", label: "Tracker", icon: KanbanSquare },
  { to: "/history", label: "Company briefs", icon: FileText },
  { to: "/briefs/new", label: "New brief", icon: Sparkles, end: true },
];

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV.map(({ to, label, icon: Icon, end }) => {
        // Brief pages (/briefs/:id) belong under "Company briefs", not "New brief".
        const briefDetail =
          to === "/history" && pathname.startsWith("/briefs/") && pathname !== "/briefs/new";
        return (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive || briefDetail
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )
            }
          >
            <Icon className="size-4 shrink-0" aria-hidden />
            {label}
          </NavLink>
        );
      })}
    </nav>
  );
}

function SidebarFooterNote() {
  return (
    <p className="px-3 text-xs leading-relaxed text-muted-foreground">
      Never scrapes, never auto-applies, never sends a message for you.
    </p>
  );
}

function DemoBanner() {
  const { user } = useAuth();
  const config = usePublicConfig();
  if (!user?.is_demo) return null;
  const left = config.llm_actions_left_today;
  return (
    <div
      role="note"
      className="mb-6 flex items-start gap-2.5 rounded-lg border bg-muted/50 px-3.5 py-2.5 text-sm text-muted-foreground"
    >
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
      <p>
        You're in the shared demo account. Anything you change is reset when the server restarts.
        {left !== null && (
          <>
            {" "}
            {left} AI {left === 1 ? "action" : "actions"} (briefs, resume tailoring) left today across all
            visitors.
          </>
        )}
      </p>
    </div>
  );
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();

  // Lock page scroll behind the open drawer; Escape closes it.
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMobileOpen(false);
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [mobileOpen]);

  // Scroll to the top on navigation, like a normal page load.
  useEffect(() => {
    window.scrollTo?.(0, 0);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <Link to="/jobs" className="flex h-16 items-center px-5">
          <Brand />
        </Link>
        <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-4">
          <NavItems />
        </div>
        <div className="flex flex-col gap-3 border-t border-sidebar-border p-3">
          <SidebarFooterNote />
          <SidebarUserMenu />
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/85 px-3 backdrop-blur-md lg:hidden">
        <Button variant="ghost" size="icon" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
          <Menu aria-hidden />
        </Button>
        <Link to="/jobs" className="flex-1">
          <Brand subtitle={false} />
        </Link>
        <CompactUserMenu />
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r bg-sidebar shadow-xl">
            <div className="flex h-14 items-center justify-between px-4">
              <Brand />
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Close navigation"
                onClick={() => setMobileOpen(false)}
              >
                <X aria-hidden />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </div>
            <div className="border-t p-4">
              <SidebarFooterNote />
            </div>
          </div>
        </div>
      )}

      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          <DemoBanner />
          <Suspense
            fallback={
              <div>
                <Skeleton className="mb-3 h-8 w-48" />
                <Skeleton className="mb-8 h-4 w-80 max-w-full" />
                <ListSkeleton rows={4} />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
