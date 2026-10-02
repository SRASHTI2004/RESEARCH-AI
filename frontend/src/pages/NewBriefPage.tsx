import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { newBriefSchema, type NewBriefFormValues } from "../validation";

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
      navigate(`/briefs/${job.id}`);
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Could not start research");
    }
  }

  return (
    <div>
      <h1>New Company Research Brief</h1>
      <p className="hint">
        Enter a company name to get a sourced brief: overview, recent news, tech stack, interview prep.
      </p>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <label>
          Company name
          <input placeholder="e.g. Razorpay" {...register("company")} />
        </label>
        {errors.company && <p className="field-error">{errors.company.message}</p>}
        {serverError && <p className="field-error">{serverError}</p>}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Starting…" : "Generate Brief"}
        </button>
      </form>
    </div>
  );
}
