"use client";

import { useCallback, useRef } from "react";

/**
 * A soft light that follows the cursor across a panel.
 *
 * Cheap in the way that matters: the mouse handler writes two CSS custom
 * properties and nothing else. No React state, so no re-render on mousemove —
 * which is the mistake that turns this effect from "polished" into "why is
 * this page dropping frames".
 *
 * The gradient itself lives in a pseudo-element that only becomes visible on
 * hover, so an idle page renders nothing extra at all.
 */
export function Spotlight({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const node = ref.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    node.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    node.style.setProperty("--my", `${e.clientY - rect.top}px`);
  }, []);

  return (
    <div ref={ref} onMouseMove={onMove} className={`spotlight ${className}`}>
      {children}
    </div>
  );
}
