import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2, Trash2 } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import type { Application, ApplicationStatus, ApplicationUpdate } from "../api/types";
import { cn, errorMessage, formatDate } from "../lib/utils";
import { followUpState, STATUS_LABELS, STATUSES } from "../tracker";
import { InlineError } from "./states";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input, Textarea } from "./ui/input";
import { Label } from "./ui/label";
import { NativeSelect } from "./ui/select";

const FOLLOW_UP_TEXT = { none: "", overdue: "Overdue", today: "Due today", upcoming: "" } as const;

export function ApplicationEditor({
  application,
  compact = false,
}: {
  application: Application;
  compact?: boolean;
}) {
  const queryClient = useQueryClient();
  const id = useId();
  const [notes, setNotes] = useState(application.notes);
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: (body: ApplicationUpdate) => api.updateApplication(application.id, body),
    onSuccess: (_, body) => {
      setError(null);
      if (body.status)
        toast.success(`Moved to ${STATUS_LABELS[body.status]}`, { description: application.title });
      else if (body.notes !== undefined) toast.success("Notes saved");
      else if ("follow_up_on" in body)
        toast.success(
          body.follow_up_on ? `Follow-up set for ${formatDate(body.follow_up_on)}` : "Follow-up cleared",
        );
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Could not save";
      setError(message);
      toast.error(message);
    },
  });

  const remove = useMutation({
    mutationFn: () => api.deleteApplication(application.id),
    onSuccess: () => {
      toast.success("Removed from tracker", { description: application.title });
      return queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(errorMessage(err, "Could not remove")),
  });

  const state = followUpState(application.follow_up_on, application.status);

  return (
    <div className="application-editor flex flex-col gap-4">
      <div
        className={cn(
          "grid gap-3",
          compact ? "grid-cols-1" : "sm:grid-cols-[minmax(0,12rem)_minmax(0,11rem)_1fr]",
        )}
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${id}-status`} className="text-xs text-muted-foreground">
            Status
          </Label>
          <NativeSelect
            id={`${id}-status`}
            value={application.status}
            onChange={(e) => update.mutate({ status: e.target.value as ApplicationStatus })}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${id}-follow-up`} className="text-xs text-muted-foreground">
            Follow up on
          </Label>
          <Input
            id={`${id}-follow-up`}
            type="date"
            value={application.follow_up_on ?? ""}
            onChange={(e) => update.mutate({ follow_up_on: e.target.value || null })}
          />
        </div>
        <div className="flex flex-wrap items-end gap-2 pb-1.5">
          {FOLLOW_UP_TEXT[state] && (
            <Badge
              variant={state === "overdue" ? "destructive" : "warning"}
              className={`follow-up follow-up-${state}`}
            >
              {FOLLOW_UP_TEXT[state]}
            </Badge>
          )}
          {application.applied_on && (
            <span className="text-xs text-muted-foreground">
              Applied {formatDate(application.applied_on)}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${id}-notes`} className="text-xs text-muted-foreground">
          Notes
        </Label>
        <Textarea
          id={`${id}-notes`}
          rows={compact ? 4 : 3}
          value={notes}
          placeholder="Who you contacted, interview dates, what to prepare…"
          onChange={(e) => setNotes(e.target.value)}
          onBlur={() => notes !== application.notes && update.mutate({ notes })}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          {update.isPending ? (
            <>
              <Loader2 className="size-3 animate-spin" aria-hidden /> Saving…
            </>
          ) : (
            <>
              <Check className="size-3" aria-hidden /> Notes save when you click away.
            </>
          )}
        </span>
        <Button
          variant="ghost-destructive"
          size="sm"
          disabled={remove.isPending}
          onClick={() => {
            if (window.confirm(`Stop tracking "${application.title}"?`)) remove.mutate();
          }}
        >
          <Trash2 aria-hidden /> Remove from tracker
        </Button>
      </div>
      {error && <InlineError>{error}</InlineError>}
    </div>
  );
}
