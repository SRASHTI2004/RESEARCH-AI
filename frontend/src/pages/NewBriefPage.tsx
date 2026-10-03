import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  BookOpenCheck,
  Loader2,
  PenLine,
  Search,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import { FormField } from "../components/FormField";
import { PageHeader } from "../components/layout/PageHeader";
import { InlineError } from "../components/states";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { newBriefSchema, type NewBriefFormValues } from "../validation";

const PIPELINE: { icon: LucideIcon; name: string; body: string }[] = [
  {
    icon: Search,
    name: "Researcher",
    body: "Searches the web and writes notes with a citation on every claim.",
  },
  {
    icon: BookOpenCheck,
    name: "Analyzer",
    body: "Organizes them into overview, news, tech stack and interview prep.",
  },
  { icon: PenLine, name: "Writer", body: "Produces the final brief with a numbered source list." },
  { icon: ShieldCheck, name: "Reviewer", body: "Flags any claim with a missing or invalid citation." },
];

export function NewBriefPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<NewBriefFormValues>({ resolver: zodResolver(newBriefSchema) });

  async function onSubmit(values: NewBriefFormValues) {
    setServerError(null);
    try {
      const job = await api.createResearch(values.company);
      toast.success(`Researching ${values.company}…`, { description: "This usually takes a minute or two." });
      navigate(`/briefs/${job.id}`);
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Could not start research");
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="New Company Research Brief"
        description="Enter a company name to get a sourced brief: overview, recent news, tech stack, interview prep."
      />

      <Card>
        <CardContent className="sm:p-8">
          <form
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            className="flex flex-col gap-4 sm:flex-row sm:items-start"
          >
            <div className="flex-1">
              <FormField
                label="Company name"
                placeholder="e.g. Razorpay"
                autoFocus
                error={errors.company?.message}
                {...register("company")}
              />
            </div>
            <Button type="submit" size="lg" disabled={isSubmitting} className="sm:mt-[1.375rem]">
              {isSubmitting ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden /> Starting…
                </>
              ) : (
                <>
                  Generate Brief <ArrowRight aria-hidden />
                </>
              )}
            </Button>
          </form>
          {serverError && <InlineError className="mt-3">{serverError}</InlineError>}
        </CardContent>
      </Card>

      <h2 className="mt-10 mb-4 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
        How it works
      </h2>
      <ol className="grid gap-3 sm:grid-cols-2">
        {PIPELINE.map(({ icon: Icon, name, body }, i) => (
          <li key={name} className="flex gap-3 rounded-xl border bg-card/60 p-4">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Icon className="size-4" aria-hidden />
            </span>
            <span>
              <span className="block text-sm font-medium">
                <span className="text-muted-foreground tabular-nums">{i + 1}.</span> {name}
              </span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{body}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
