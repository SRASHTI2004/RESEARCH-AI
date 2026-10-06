import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, ArrowRight, Loader2, PlayCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { FormField } from "../components/FormField";
import { AuthLayout } from "../components/layout/AuthLayout";
import { Alert, AlertTitle } from "../components/ui/alert";
import { Button } from "../components/ui/button";
import { usePublicConfig } from "../lib/publicConfig";
import { loginSchema, type LoginFormValues } from "../validation";

export function LoginPage() {
  const { login, loginAsDemo } = useAuth();
  const navigate = useNavigate();
  const config = usePublicConfig();
  const [serverError, setServerError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginFormValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      navigate("/");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Login failed");
    }
  }

  async function tryDemo() {
    setServerError(null);
    setDemoLoading(true);
    try {
      await loginAsDemo();
      navigate("/");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Couldn't open the demo");
      setDemoLoading(false);
    }
  }

  return (
    <AuthLayout>
      <h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2>
      <p className="mt-1.5 text-sm text-muted-foreground">Log in to see today's matches.</p>

      {config.demo_enabled && (
        <div className="mt-8 rounded-xl border bg-muted/40 p-4">
          <p className="text-sm font-medium">Just looking around?</p>
          <p className="mt-1 text-sm text-muted-foreground">
            The demo account has real postings scored by the app, a sample tracker and company briefs. No
            sign-up needed.
          </p>
          <Button size="lg" className="mt-4 w-full" onClick={tryDemo} disabled={demoLoading}>
            {demoLoading ? (
              <>
                <Loader2 className="animate-spin" aria-hidden /> Opening the demo…
              </>
            ) : (
              <>
                <PlayCircle aria-hidden /> Try the demo
              </>
            )}
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-8 flex flex-col gap-5">
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />

        {serverError && (
          <Alert variant="destructive" role="alert">
            <AlertCircle aria-hidden />
            <AlertTitle className="field-error">{serverError}</AlertTitle>
          </Alert>
        )}

        <Button
          type="submit"
          size="lg"
          variant={config.demo_enabled ? "outline" : "default"}
          disabled={isSubmitting}
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="animate-spin" aria-hidden /> Logging in…
            </>
          ) : (
            <>
              Log in <ArrowRight aria-hidden />
            </>
          )}
        </Button>
      </form>

      {config.registration_enabled && (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          No account?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create one
          </Link>
        </p>
      )}
    </AuthLayout>
  );
}
