import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, tokenStorage } from "../api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("login stores both tokens", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(jsonResponse({ access_token: "a1", refresh_token: "r1", token_type: "bearer" })),
    );

    await api.login("a@b.com", "password123");

    expect(tokenStorage.getAccessToken()).toBe("a1");
    expect(tokenStorage.getRefreshToken()).toBe("r1");
  });

  it("refreshes once on a 401 and retries the original request", async () => {
    tokenStorage.setTokens({ access_token: "expired", refresh_token: "r1", token_type: "bearer" });

    const fetchMock = vi
      .fn()
      // 1. original request -> 401 (expired access token)
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      // 2. refresh request -> new token pair
      .mockResolvedValueOnce(jsonResponse({ access_token: "a2", refresh_token: "r2", token_type: "bearer" }))
      // 3. retried original request -> succeeds
      .mockResolvedValueOnce(jsonResponse({ id: "job-1", status: "done" }));

    vi.stubGlobal("fetch", fetchMock);

    const result = await api.getResearch("job-1");

    expect(result).toEqual({ id: "job-1", status: "done" });
    expect(tokenStorage.getAccessToken()).toBe("a2");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("clears tokens and throws an ApiError if refresh also fails", async () => {
    tokenStorage.setTokens({ access_token: "expired", refresh_token: "bad", token_type: "bearer" });

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "invalid refresh token" }, 401));

    vi.stubGlobal("fetch", fetchMock);

    await expect(api.getResearch("job-1")).rejects.toBeInstanceOf(ApiError);
    expect(tokenStorage.getAccessToken()).toBeNull();
  });

  it("surfaces a Pydantic-style validation error as a readable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ detail: [{ msg: "company cannot be blank", type: "value_error" }] }, 422),
        ),
    );

    await expect(api.createResearch("")).rejects.toThrow("company cannot be blank");
  });
});
