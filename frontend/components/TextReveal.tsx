"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Masked word-by-word reveal — the signature move of high-end studio sites.
 *
 * The mechanic is simple and the detail is everything: each word sits inside a
 * container with `overflow: hidden`, and the word itself starts translated
 * fully below that container's baseline. As it slides up it appears to emerge
 * from behind a hard edge rather than fading in. Fading reads as a web page;
 * this reads as type being set.
 *
 * Two things keep it from looking amateurish:
 *
 * 1. The stagger is small (~38ms). Any slower and long headings turn into a
 *    performance the reader has to sit through.
 * 2. Line height has to leave room, hence the padding-bottom on the mask —
 *    without it, descenders on g, y, p get clipped at rest, which looks like
 *    a rendering bug rather than a choice.
 *
 * Screen readers get the whole string from an sr-only copy; the animated
 * version is hidden from the accessibility tree, so nobody hears a heading
 * read out one word at a time.
 */
export function TextReveal({
  text,
  className = "",
  delay = 0,
  stagger = 38,
  as: Tag = "span",
}: {
  text: string;
  className?: string;
  delay?: number;
  stagger?: number;
  as?: "span" | "h1" | "h2" | "p";
}) {
  // Typed loosely on purpose: `as` is a union of intrinsic tags, and TypeScript
  // can't narrow the props of a union-typed JSX component without a great deal
  // of generic machinery for no practical gain here.
  const Component = Tag as React.ElementType;

  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setShown(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const words = text.split(" ");

  return (
    <Component
      ref={ref}
      className={className}
      // The words below are marked aria-hidden, so the label carries the
      // actual text — a screen reader reads one sentence, not a word list.
      aria-label={text}
    >
      <span aria-hidden="true">
        {words.map((word, i) => (
          <span
            key={`${word}-${i}`}
            className="inline-block overflow-hidden pb-[0.14em] align-bottom"
          >
            <span
              className="inline-block will-change-transform"
              style={{
                transform: shown ? "translateY(0)" : "translateY(110%)",
                opacity: shown ? 1 : 0,
                transition:
                  "transform 0.9s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.6s ease-out",
                transitionDelay: `${delay + i * stagger}ms`,
              }}
            >
              {word}
            </span>
            {i < words.length - 1 && <span>&nbsp;</span>}
          </span>
        ))}
      </span>
    </Component>
  );
}
