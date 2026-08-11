/**
 * The project mark.
 *
 * Drawn rather than pulled from an icon set. A shield or padlock from a
 * library is the visual equivalent of a placeholder: it says "security-ish"
 * and nothing else, and anyone who has seen a few dashboards recognises it
 * instantly as the default choice.
 *
 * This is three stacked bars of decreasing width, gated by a vertical rule.
 * The stack is the inventory, the decreasing widths are the risk tiers, and
 * the rule is the gate a model has to clear to move up. It survives being
 * shrunk to 16px, which is the only real test a mark has to pass.
 */
export function Logo({
  className = "",
  size = 22,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      {/* The gate */}
      <path
        d="M4.5 3.5V20.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.45"
      />
      {/* Three tiers, widest at the bottom — most models sit low, few reach
          the top, which is the shape of any real registry */}
      <rect x="8" y="4.5" width="6" height="3.6" rx="1.2" fill="currentColor" opacity="0.5" />
      <rect x="8" y="10.2" width="9.5" height="3.6" rx="1.2" fill="currentColor" opacity="0.75" />
      <rect x="8" y="15.9" width="12" height="3.6" rx="1.2" fill="currentColor" />
    </svg>
  );
}
