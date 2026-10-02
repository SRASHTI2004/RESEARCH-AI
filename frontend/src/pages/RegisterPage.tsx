import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { registerSchema, type RegisterFormValues } from "../validation";

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterFormValues) {
    setServerError(null);
    try {
      await registerUser(values.email, values.password);
      navigate("/");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Registration failed");
    }
  }

  return (
    <div className="auth-page">
      <h1>Create an account</h1>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <label>
          Email
          <input type="email" autoComplete="email" {...register("email")} />
        </label>
        {errors.email && <p className="field-error">{errors.email.message}</p>}

        <label>
          Password
          <input type="password" autoComplete="new-password" {...register("password")} />
        </label>
        {errors.password && <p className="field-error">{errors.password.message}</p>}

        {serverError && <p className="field-error">{serverError}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Register"}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
