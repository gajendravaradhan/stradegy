import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function usePullToRefresh() {
  const queryClient = useQueryClient();
  const startY = useRef(0);
  const isPulling = useRef(false);
  const threshold = 80;

  const onTouchStart = useCallback((e: TouchEvent) => {
    if (window.scrollY === 0) {
      startY.current = e.touches[0].clientY;
      isPulling.current = true;
    }
  }, []);

  const onTouchMove = useCallback((e: TouchEvent) => {
    if (!isPulling.current) return;
    const delta = e.touches[0].clientY - startY.current;
    if (delta > threshold) {
      isPulling.current = false;
      queryClient.invalidateQueries();
    }
  }, [queryClient]);

  const onTouchEnd = useCallback(() => {
    isPulling.current = false;
  }, []);

  useEffect(() => {
    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd);
    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [onTouchStart, onTouchMove, onTouchEnd]);
}
