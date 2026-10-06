import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { PublicConfig } from "../api/types";

/** Used when /config can't be reached (older API, network hiccup): behave like a normal local install. */
export const DEFAULT_PUBLIC_CONFIG: PublicConfig = {
  registration_enabled: true,
  demo_enabled: false,
  llm_actions_left_today: null,
};

export function usePublicConfig(): PublicConfig {
  const { data } = useQuery({
    queryKey: ["public-config"],
    queryFn: () => api.publicConfig(),
    staleTime: 60_000,
    retry: false,
  });
  return data ?? DEFAULT_PUBLIC_CONFIG;
}
