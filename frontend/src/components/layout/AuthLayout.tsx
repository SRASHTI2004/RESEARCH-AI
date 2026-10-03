import { Bell, FileSearch, KanbanSquare, ShieldCheck, Target, Wand2, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Brand } from "./Brand";
import { ThemeToggle } from "./UserMenu";

/** The one-sentence pitch, shared by the landing panel and the page's meta description. */
export const TAGLINE =
  "ResearchAI finds fresh developer jobs every day, scores them against your profile, and helps you apply with a tracker, referral drafts, honest resume tailoring and cited company research.";

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Target,
    title: "Scored daily matches",
    body: "Official job boards and free APIs, ranked 0–100 for you.",
  },
  { icon: Bell, title: "Telegram + email digest", body: "Your top 10 new roles every morning." },
  { icon: KanbanSquare, title: "Application tracker", body: "Saved → applied → interview, with follow-ups." },
  { icon: Wand2, title: "Resume tailoring", body: "Rewords your real experience — never invents any." },
  {
    icon: FileSearch,
    title: "Company research briefs",
    body: "Multi-agent research with clickable citations.",
  },
];

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1.1fr_1fr]">
      {/* Landing panel */}
      <section className="relative hidden overflow-hidden bg-[oklch(0.22_0.06_275)] text-white lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_20%_10%,oklch(0.55_0.22_280/0.55),transparent),radial-gradient(50%_45%_at_90%_90%,oklch(0.6_0.2_300/0.35),transparent)]"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(white_1px,transparent_1px),linear-gradient(90deg,white_1px,transparent_1px)] [background-size:44px_44px]"
        />
        <Brand className="relative [&_span.text-muted-foreground]:text-white/60" />

        <div className="relative max-w-xl">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-white/80">
            <ShieldCheck className="size-3.5" aria-hidden /> No scraping · no auto-apply · nothing sent for
            you
          </p>
          <h1 className="text-4xl leading-[1.1] font-semibold tracking-tight text-balance xl:text-5xl">
            Your job search, on autopilot — minus the spam.
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-white/75">{TAGLINE}</p>

          <ul className="mt-10 grid gap-4 sm:grid-cols-2">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon className="size-4" aria-hidden />
                </span>
                <span>
                  <span className="block text-sm font-medium">{title}</span>
                  <span className="block text-sm text-white/60">{body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/50">
          FastAPI · LangGraph · React · TypeScript · Tailwind CSS
        </p>
      </section>

      {/* Form panel */}
      <section className="relative flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between lg:justify-end">
          <Brand className="lg:hidden" />
          <ThemeToggle />
        </div>
        <div className="flex flex-1 flex-col items-center justify-center py-10">
          <div className="w-full max-w-sm">
            <p className="mb-8 text-sm leading-relaxed text-muted-foreground lg:hidden">{TAGLINE}</p>
            {children}
          </div>
        </div>
      </section>
    </div>
  );
}
