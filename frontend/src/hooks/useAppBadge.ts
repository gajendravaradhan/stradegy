import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAlerts } from "../lib/api";

declare global {
  interface Navigator {
    setAppBadge?: (count: number) => Promise<void>;
    clearAppBadge?: () => Promise<void>;
  }
}

export function useAppBadge() {
  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => getAlerts(),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    if (!navigator.setAppBadge) return;
    const pendingCount = (alerts || []).filter((a) => a.status === "pending").length;
    if (pendingCount > 0) {
      navigator.setAppBadge(pendingCount).catch(() => {});
    } else {
      navigator.clearAppBadge?.().catch(() => {});
    }
  }, [alerts]);
}
