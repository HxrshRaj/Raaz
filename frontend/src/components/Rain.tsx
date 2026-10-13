import { useMemo } from "react";

/** CSS-only rain. Drops are positioned once; animation is disabled by prefers-reduced-motion / the in-app setting. */
export function Rain({ count = 70, opacity = 1 }: { count?: number; opacity?: number }) {
  const drops = useMemo(
    () => Array.from({ length: count }, (_, i) => ({
      left: `${(i * 97) % 100 + ((i * 13) % 7) / 10}%`,
      delay: `${-((i * 37) % 100) / 40}s`,
      duration: `${0.7 + ((i * 17) % 10) / 14}s`,
      height: `${9 + ((i * 29) % 9)}%`,
      op: 0.25 + ((i * 11) % 6) / 10,
    })),
    [count],
  );
  return (
    <div className="rain" aria-hidden style={{ opacity }}>
      {drops.map((d, i) => (
        <i key={i} style={{ left: d.left, animationDelay: d.delay, animationDuration: d.duration, height: d.height, opacity: d.op }} />
      ))}
    </div>
  );
}
