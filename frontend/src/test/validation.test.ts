import { describe, expect, it } from "vitest";
import { loginSchema, newBriefSchema, registerSchema } from "../validation";

describe("loginSchema", () => {
  it("accepts a valid email/password", () => {
    const result = loginSchema.safeParse({ email: "a@b.com", password: "x" });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("rejects a password shorter than 8 characters", () => {
    const result = registerSchema.safeParse({ email: "a@b.com", password: "short" });
    expect(result.success).toBe(false);
  });

  it("accepts an 8+ character password", () => {
    const result = registerSchema.safeParse({ email: "a@b.com", password: "password123" });
    expect(result.success).toBe(true);
  });
});

describe("newBriefSchema", () => {
  it("rejects a blank company name", () => {
    const result = newBriefSchema.safeParse({ company: "   " });
    expect(result.success).toBe(false);
  });

  it("trims whitespace from a valid company name", () => {
    const result = newBriefSchema.safeParse({ company: "  Acme Corp  " });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.company).toBe("Acme Corp");
  });
});
