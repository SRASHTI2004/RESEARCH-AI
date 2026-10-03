import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, ExternalLink, Info, Users } from "lucide-react";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";
import { api } from "../api/client";
import type { Application } from "../api/types";
import { errorMessage } from "../lib/utils";
import { CopyButton } from "./CopyButton";
import { ErrorState, ProseSkeleton } from "./states";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Checkbox } from "./ui/label";

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="relative pl-10">
      <span className="absolute top-0 left-0 flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
        {n}
      </span>
      <h3 className="mb-3 pt-1 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export function ReferralPanel({ jobId, application }: { jobId: string; application?: Application }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["referral", jobId],
    queryFn: () => api.getReferralKit(jobId),
    enabled: open,
  });

  const markAsked = useMutation({
    mutationFn: async () =>
      application
        ? api.updateApplication(application.id, { status: "referral_asked" })
        : api.createApplication({ job_id: jobId, status: "referral_asked" }),
    onSuccess: () => {
      toast.success("Marked as referral asked", { description: "We'll keep it in your tracker." });
      return queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(errorMessage(err, "Could not update the tracker")),
  });

  const asked = application?.status === "referral_asked";

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="flex size-7 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Users className="size-4" aria-hidden />
          </span>
          Referral helper
        </CardTitle>
        <CardDescription>
          Search strings to paste into LinkedIn, where to look, and message drafts. Nothing is sent for you.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!open ? (
          <Button variant="outline" onClick={() => setOpen(true)}>
            Show referral helper <ChevronDown aria-hidden />
          </Button>
        ) : (
          <>
            {isLoading && <ProseSkeleton lines={5} />}
            {error && (
              <ErrorState
                title="Could not build the referral kit."
                message={errorMessage(error, "Try again in a moment.")}
                onRetry={() => void refetch()}
              />
            )}
            {data && (
              <div className="referral flex flex-col gap-8">
                {data.notes.length > 0 && (
                  <div className="flex gap-2.5 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
                    <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
                    <div className="flex flex-col gap-1">
                      {data.notes.map((n) => (
                        <p key={n}>{n}</p>
                      ))}
                    </div>
                  </div>
                )}

                <Step n={1} title="Find people">
                  <ul className="search-strings flex flex-col divide-y rounded-lg border">
                    {data.search_strings.map((s) => (
                      <li key={s.query} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">
                            {s.label} <span className="font-normal text-muted-foreground">· {s.where}</span>
                          </p>
                          <code className="mt-1.5 block rounded-md bg-muted px-2 py-1 font-mono text-xs break-words">
                            {s.query}
                          </code>
                        </div>
                        <div className="row-actions flex shrink-0 gap-2">
                          <CopyButton text={s.query} />
                          <Button asChild variant="outline" size="sm">
                            <a href={s.url} target="_blank" rel="noopener noreferrer">
                              <ExternalLink aria-hidden />
                              Open search
                            </a>
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </Step>

                <Step n={2} title="Where to look">
                  <ul className="checklist flex flex-col gap-2.5">
                    {data.checklist.map((item) => (
                      <li key={item}>
                        <label className="flex cursor-pointer items-start gap-2.5 text-sm has-[:checked]:text-muted-foreground has-[:checked]:line-through">
                          <Checkbox className="mt-0.5" /> {item}
                        </label>
                      </li>
                    ))}
                  </ul>
                </Step>

                <Step n={3} title="Message drafts">
                  <div className="flex flex-col gap-4">
                    {data.drafts.map((d) => (
                      <div key={d.kind} className="draft overflow-hidden rounded-lg border">
                        <div className="draft-header flex items-center gap-3 border-b bg-muted/40 px-3 py-2">
                          <strong className="flex-1 text-sm font-medium">{d.title}</strong>
                          <span className="text-xs text-muted-foreground tabular-nums">
                            {d.char_count} chars
                          </span>
                          <CopyButton text={d.body} />
                        </div>
                        {/* Drafts are meant to be pasted verbatim, so they stay plain text. */}
                        <p className="p-3 text-sm leading-relaxed whitespace-pre-wrap">{d.body}</p>
                      </div>
                    ))}
                  </div>
                </Step>

                <div className="flex justify-end border-t pt-5">
                  <Button disabled={markAsked.isPending || asked} onClick={() => markAsked.mutate()}>
                    {asked && <CheckCircle2 aria-hidden />}
                    {asked ? "Marked as referral asked" : "I asked for a referral"}
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
