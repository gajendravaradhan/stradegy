import { useEffect, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";

interface Tab {
  path: string;
  label: string;
}

function isInsideHorizontallyScrollable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  let el: HTMLElement | null = target;
  while (el) {
    const style = window.getComputedStyle(el);
    if (
      style.overflowX === "auto" ||
      style.overflowX === "scroll" ||
      style.overflow === "auto" ||
      style.overflow === "scroll"
    ) {
      return true;
    }
    el = el.parentElement;
  }
  return false;
}

function isInteractiveElement(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "svg" || tag === "canvas" || tag === "input" || tag === "textarea" || tag === "select") {
    return true;
  }
  return false;
}

export function useSwipeNavigation(tabs: Tab[]) {
  const navigate = useNavigate();
  const location = useLocation();
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const isHorizontal = useRef(false);

  const onTouchStart = useCallback((e: TouchEvent) => {
    if (isInteractiveElement(e.target) || isInsideHorizontallyScrollable(e.target)) {
      touchStart.current = null;
      return;
    }
    touchStart.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    };
    isHorizontal.current = false;
  }, []);

  const onTouchMove = useCallback((e: TouchEvent) => {
    if (!touchStart.current) return;
    const deltaX = e.touches[0].clientX - touchStart.current.x;
    const deltaY = e.touches[0].clientY - touchStart.current.y;

    if (Math.abs(deltaX) > Math.abs(deltaY) * 1.5 && Math.abs(deltaX) > 30) {
      isHorizontal.current = true;
    }
  }, []);

  const onTouchEnd = useCallback((e: TouchEvent) => {
    if (!touchStart.current) return;

    const deltaX = e.changedTouches[0].clientX - touchStart.current.x;
    const deltaY = e.changedTouches[0].clientY - touchStart.current.y;

    touchStart.current = null;

    if (!isHorizontal.current) return;
    if (Math.abs(deltaX) < 60) return;
    if (Math.abs(deltaX) <= Math.abs(deltaY) * 1.5) return;

    const currentIndex = tabs.findIndex(
      (tab) =>
        tab.path === location.pathname ||
        (tab.path !== "/" && location.pathname.startsWith(tab.path))
    );

    if (currentIndex === -1) return;

    if (deltaX < 0) {
      const nextIndex = Math.min(currentIndex + 1, tabs.length - 1);
      if (nextIndex !== currentIndex) {
        navigate(tabs[nextIndex].path);
      }
    } else {
      const prevIndex = Math.max(currentIndex - 1, 0);
      if (prevIndex !== currentIndex) {
        navigate(tabs[prevIndex].path);
      }
    }
  }, [tabs, navigate, location.pathname]);

  useEffect(() => {
    const main = document.querySelector("main");
    if (!main) return;

    main.addEventListener("touchstart", onTouchStart, { passive: true });
    main.addEventListener("touchmove", onTouchMove, { passive: true });
    main.addEventListener("touchend", onTouchEnd);

    return () => {
      main.removeEventListener("touchstart", onTouchStart);
      main.removeEventListener("touchmove", onTouchMove);
      main.removeEventListener("touchend", onTouchEnd);
    };
  }, [onTouchStart, onTouchMove, onTouchEnd]);
}
