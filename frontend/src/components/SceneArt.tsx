import { useId, type ReactNode } from "react";

/** Original, hand-built SVG backdrops for each location (viewBox 100x60). No stock imagery or third-party art. */

function Defs({ id }: { id: string }) {
  return (
    <defs>
      <linearGradient id={`sky${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#070b12" /><stop offset="1" stopColor="#1b2740" /></linearGradient>
      <linearGradient id={`wet${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1a2233" /><stop offset="1" stopColor="#0a0e16" /></linearGradient>
      <radialGradient id={`glow${id}`}><stop offset="0" stopColor="#f2a94e" stopOpacity="0.9" /><stop offset="1" stopColor="#f2a94e" stopOpacity="0" /></radialGradient>
      <radialGradient id={`cool${id}`}><stop offset="0" stopColor="#7fb2ff" stopOpacity="0.55" /><stop offset="1" stopColor="#7fb2ff" stopOpacity="0" /></radialGradient>
      <linearGradient id={`wood${id}`} x1="0" x2="1"><stop offset="0" stopColor="#3b2416" /><stop offset="0.5" stopColor="#5a3820" /><stop offset="1" stopColor="#3b2416" /></linearGradient>
    </defs>
  );
}
const Lamp = ({ x, y, r = 14, id, cool = false }: { x: number; y: number; r?: number; id: string; cool?: boolean }) => (
  <g className="animate-flicker">
    <circle cx={x} cy={y} r={r} fill={`url(#${cool ? "cool" : "glow"}${id})`} />
    <circle cx={x} cy={y} r={0.9} fill={cool ? "#cfe3ff" : "#ffe3b0"} />
  </g>
);
const Streaks = ({ id, y = 46 }: { id: string; y?: number }) => (
  <g opacity="0.35">
    {[12, 31, 52, 74, 90].map((x) => <rect key={x} x={x} y={y} width="1.4" height={60 - y} fill={`url(#glow${id})`} />)}
  </g>
);

function Platform({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill={`url(#sky${id})`} />
      <path d="M0 14 L100 6 M0 20 L100 12 M10 14 L10 10 M30 12 L30 8 M50 10 L50 6 M70 9 L70 5 M90 7 L90 4" stroke="#2a3547" strokeWidth="0.6" />
      <rect x="0" y="0" width="100" height="5" fill="#0a0e16" />
      {[8, 34, 66, 92].map((x) => <rect key={x} x={x} y="14" width="2.2" height="34" fill="#1a2233" />)}
      <circle cx="50" cy="13" r="5.2" fill="#e9e2d0" stroke="#7d6130" strokeWidth="0.8" />
      <path d="M50 13 L50 9.6 M50 13 L52.6 14.3" stroke="#10151f" strokeWidth="0.6" />
      <rect x="3" y="26" width="24" height="12" rx="0.8" fill="#10151f" stroke="#7d6130" strokeWidth="0.5" />
      {[0, 1, 2, 3].map((i) => <rect key={i} x="5" y={28 + i * 2.4} width="20" height="0.7" fill="#8e98a8" opacity="0.6" />)}
      <rect x="60" y="30" width="38" height="12" rx="1" fill="#0f1520" />
      <rect x="62" y="32" width="34" height="5" fill="#1d2636" /><circle cx="68" cy="43" r="1.4" fill="#0a0e16" /><circle cx="90" cy="43" r="1.4" fill="#0a0e16" />
      <rect x="0" y="48" width="100" height="12" fill={`url(#wet${id})`} />
      <path d="M0 52 L100 52 M0 56 L100 56" stroke="#2a3547" strokeWidth="0.5" />
      {[10, 46, 82].map((x) => <Lamp key={x} x={x} y={13} id={id} />)}
      <Streaks id={id} />
    </>
  );
}
function Carriage({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#1b110b" />
      {Array.from({ length: 14 }).map((_, i) => <rect key={i} x={i * 7.2} y="0" width="7" height="40" fill={`url(#wood${id})`} opacity={0.9 - (i % 2) * 0.1} />)}
      <rect x="0" y="38" width="100" height="22" fill="#150d08" />
      <path d="M0 40 L100 40" stroke="#b8924f" strokeWidth="0.6" />
      <rect x="62" y="6" width="22" height="20" rx="1" fill="#0a1220" stroke="#b8924f" strokeWidth="0.8" />
      <path d="M64 8 L66 20 M70 8 L72 24 M76 8 L77 18 M80 9 L81 23" stroke="#7fa0c8" strokeWidth="0.3" opacity="0.7" />
      <rect x="48" y="38" width="30" height="3" fill="#3b2416" /><rect x="50" y="41" width="2" height="10" fill="#2a1a10" /><rect x="74" y="41" width="2" height="10" fill="#2a1a10" />
      <rect x="86" y="8" width="11" height="42" rx="1" fill="#2a1a10" stroke="#b8924f" strokeWidth="0.6" /><circle cx="88.4" cy="30" r="0.9" fill="#d9b572" />
      <rect x="10" y="30" width="16" height="16" rx="3" fill="#3a1e16" stroke="#6a3b25" strokeWidth="0.6" />
      <ellipse cx="38" cy="50" rx="10" ry="3" fill="#0a0604" opacity="0.9" />
      <path d="M30 48 Q36 44 44 48 Q48 52 42 54 Q34 55 30 48Z" fill="none" stroke="#e9e2d0" strokeWidth="0.35" strokeDasharray="1 0.8" />
      <rect x="62" y="30" width="3" height="7" fill="#2a2a2a" /><circle cx="63.5" cy="28" r="2" fill="#f2a94e" opacity="0.5" />
      <Lamp x={63.5} y={27} r={22} id={id} /> <Lamp x={30} y={6} r={16} id={id} />
    </>
  );
}
function Office({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#14100c" />
      <rect x="0" y="0" width="100" height="42" fill="#1c1510" />
      {[4, 16, 28].map((x) => (
        <g key={x}><rect x={x} y="6" width="10" height="30" fill="#2a1d12" stroke="#4a3320" strokeWidth="0.4" />{[0, 1, 2, 3, 4].map((r) => <rect key={r} x={x + 0.8} y={8 + r * 5.6} width="8.4" height="4.2" fill={r % 2 ? "#6a2c22" : "#2c4a3a"} opacity="0.8" />)}</g>
      ))}
      <rect x="62" y="6" width="18" height="30" fill="#10151f" stroke="#7d6130" strokeWidth="0.6" />
      {Array.from({ length: 18 }).map((_, i) => <circle key={i} cx={64.5 + (i % 6) * 2.8} cy={10 + Math.floor(i / 6) * 8} r="0.7" fill="#d9b572" />)}
      <circle cx="90" cy="14" r="5" fill="#e9e2d0" stroke="#7d6130" strokeWidth="0.6" />
      <rect x="10" y="40" width="46" height="4" fill={`url(#wood${id})`} /><rect x="12" y="44" width="3" height="14" fill="#2a1a10" /><rect x="51" y="44" width="3" height="14" fill="#2a1a10" />
      <rect x="0" y="52" width="100" height="8" fill="#0d0a07" />
      <path d="M30 20 L40 20 L38 28 L32 28Z" fill="#1f6b4a" opacity="0.9" /><line x1="35" y1="0" x2="35" y2="20" stroke="#4a3320" strokeWidth="0.4" />
      <Lamp x={35} y={30} r={20} id={id} />
    </>
  );
}
function Waiting({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#10151f" />
      <rect x="52" y="6" width="42" height="30" fill="#0a1220" stroke="#7d6130" strokeWidth="0.8" />
      {[0, 1, 2].map((i) => <line key={i} x1={66 + i * 14} y1="6" x2={66 + i * 14} y2="36" stroke="#7d6130" strokeWidth="0.5" />)}
      <path d="M56 10 L58 30 M70 8 L72 28 M84 10 L85 32" stroke="#7fa0c8" strokeWidth="0.3" opacity="0.6" />
      <Lamp x={78} y={18} r={10} id={id} cool />
      {[8, 30].map((x) => <g key={x}><rect x={x} y="36" width="18" height="3" fill={`url(#wood${id})`} /><rect x={x} y="31" width="18" height="2.2" fill="#3b2416" /><rect x={x + 1} y="39" width="2" height="12" fill="#2a1a10" /><rect x={x + 15} y="39" width="2" height="12" fill="#2a1a10" /></g>)}
      <rect x="10" y="46" width="7" height="10" rx="1" fill="#2a3547" />
      <line x1="30" y1="2" x2="30" y2="8" stroke="#4a3320" /><path d="M20 8 L40 8 M30 8 L30 4 M24 8 L26 6 M36 8 L34 6" stroke="#2a3547" strokeWidth="0.8" />
      <rect x="0" y="52" width="100" height="8" fill="#0a0e16" />
      <Lamp x={30} y={10} r={14} id={id} />
    </>
  );
}
function Security({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#0c1018" />
      {Array.from({ length: 6 }).map((_, i) => {
        const x = 8 + (i % 3) * 20, y = 10 + Math.floor(i / 3) * 16;
        return <g key={i}><rect x={x} y={y} width="18" height="13" fill="#0a1a2a" stroke="#2a3547" strokeWidth="0.5" /><rect x={x + 1} y={y + 1} width="16" height="11" fill="#12304a" opacity="0.9" /><path d={`M${x + 2} ${y + 9} L${x + 8} ${y + 5} L${x + 12} ${y + 8} L${x + 16} ${y + 3}`} stroke="#7fb2ff" strokeWidth="0.3" fill="none" opacity="0.8" /></g>;
      })}
      <rect x="62" y="22" width="24" height="16" fill="#101826" stroke="#2a3547" strokeWidth="0.5" /><rect x="64" y="24" width="20" height="10" fill="#183a2a" />
      <rect x="55" y="40" width="40" height="3" fill="#1d2636" /><rect x="0" y="50" width="100" height="10" fill="#080b11" />
      <rect x="78" y="36" width="12" height="5" fill="#1a1f2a" /><rect x="74" y="45" width="18" height="4" fill="#2a1d12" />
      <Lamp x={20} y={18} r={26} id={id} cool /> <Lamp x={74} y={30} r={18} id={id} cool />
    </>
  );
}
function Tea({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill={`url(#sky${id})`} />
      <path d="M20 14 L80 14 L88 22 L12 22Z" fill="#2a2f38" stroke="#4a5160" strokeWidth="0.5" />
      <rect x="16" y="22" width="68" height="22" fill="#2a1a10" stroke="#4a3320" strokeWidth="0.5" />
      <rect x="22" y="34" width="56" height="4" fill={`url(#wood${id})`} />
      {[28, 38, 48].map((x) => <rect key={x} x={x} y="28" width="4" height="6" rx="0.6" fill="#d9b572" opacity="0.8" />)}
      <ellipse cx="66" cy="31" rx="5" ry="3" fill="#10151f" /><ellipse cx="66" cy="29" rx="3.4" ry="1.2" fill="#f2a94e" opacity="0.8" />
      <path d="M12 22 Q30 26 50 22 T88 22" stroke="#f2a94e" strokeWidth="0.3" fill="none" />
      {[16, 28, 40, 52, 64, 76].map((x) => <circle key={x} cx={x} cy="24" r="0.8" fill="#ffe3b0" />)}
      <rect x="0" y="48" width="100" height="12" fill={`url(#wet${id})`} />
      <Lamp x={50} y={30} r={30} id={id} /> <Streaks id={id} y={48} />
    </>
  );
}
function Siding({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill={`url(#sky${id})`} />
      <rect x="0" y="22" width="100" height="1.4" fill="#10151f" />
      {Array.from({ length: 25 }).map((_, i) => <rect key={i} x={i * 4.2} y="14" width="0.7" height="9" fill="#1a2233" />)}
      <rect x="6" y="26" width="46" height="14" rx="2" fill="#10151f" stroke="#2a3547" strokeWidth="0.4" />
      {[0, 1, 2, 3, 4].map((i) => <rect key={i} x={9 + i * 8.5} y="29" width="5" height="5" fill="#f2a94e" opacity={i === 2 ? 0.8 : 0.25} />)}
      <path d="M0 60 L38 42 M100 60 L62 42 M10 60 L40 44 M90 60 L60 44" stroke="#4a5160" strokeWidth="0.7" />
      {[44, 49, 55].map((y) => <line key={y} x1={50 - (y - 42) * 1.9} y1={y} x2={50 + (y - 42) * 1.9} y2={y} stroke="#2a1d12" strokeWidth="1.1" />)}
      <rect x="0" y="52" width="40" height="8" fill="#080b11" /><path d="M2 56 Q14 54 38 56" stroke="#3a6a9a" strokeWidth="0.8" fill="none" opacity="0.7" />
      <rect x="68" y="12" width="1.2" height="30" fill="#2a3547" /><rect x="66" y="12" width="5" height="3" fill="#1a1f2a" />
      <rect x="44" y="30" width="2" height="16" fill="#4a3320" /><rect x="52" y="30" width="2" height="16" fill="#4a3320" /><rect x="44" y="30" width="10" height="1.2" fill="#6a4a30" />
      <Lamp x={30} y={16} r={22} id={id} />
    </>
  );
}
function Corp({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#0c121c" />
      {Array.from({ length: 26 }).map((_, i) => <rect key={i} x={(i * 13) % 96} y={4 + ((i * 7) % 18)} width="2.2" height="2.2" fill="#f2a94e" opacity={0.15 + (i % 4) * 0.1} />)}
      <rect x="4" y="6" width="44" height="34" fill="#101826" stroke="#2a3547" strokeWidth="0.5" /><path d="M26 6 L26 40 M4 23 L48 23" stroke="#2a3547" strokeWidth="0.5" />
      <rect x="56" y="10" width="36" height="22" fill="#d8d2c0" opacity="0.88" /><path d="M60 16 L70 14 L78 20 L88 12" stroke="#6a2c22" strokeWidth="0.6" fill="none" /><text x="60" y="28" fontSize="2.4" fill="#2a1d12">PATHFINDER v2</text>
      <rect x="10" y="40" width="30" height="3" fill="#1d2636" /><rect x="52" y="38" width="40" height="3" fill="#1d2636" />
      <rect x="0" y="50" width="100" height="10" fill="#080b11" />
      <Lamp x={25} y={18} r={18} id={id} cool />
    </>
  );
}
function Shop({ id }: { id: string }) {
  return (
    <>
      <rect width="100" height="60" fill="#150f1b" />
      {[10, 22, 34].map((y) => <g key={y}><rect x="6" y={y} width="48" height="1.2" fill="#4a3320" />{Array.from({ length: 11 }).map((_, i) => <rect key={i} x={8 + i * 4.2} y={y - 6} width="3" height="6" fill={["#c2412d", "#2c6a8a", "#b8924f", "#4a6a4a"][i % 4]} opacity="0.85" />)}</g>)}
      <rect x="60" y="8" width="34" height="9" rx="1" fill="#10151f" stroke="#e0634e" strokeWidth="0.6" /><text x="77" y="14.4" fontSize="4.6" fill="#e0634e" textAnchor="middle" fontFamily="monospace">SIM · RECHARGE</text>
      <rect x="56" y="34" width="40" height="5" fill={`url(#wood${id})`} /><rect x="58" y="39" width="3" height="14" fill="#2a1a10" /><rect x="91" y="39" width="3" height="14" fill="#2a1a10" />
      <rect x="0" y="52" width="100" height="8" fill="#0a0710" />
      <Lamp x={77} y={13} r={22} id={id} /> <Lamp x={30} y={6} r={14} id={id} />
    </>
  );
}
const SCENES: Record<string, (p: { id: string }) => ReactNode> = {
  platform: Platform, carriage: Carriage, office: Office, waiting: Waiting, security: Security, tea: Tea,
  siding: Siding, corp: Corp, shop: Shop,
};

export function SceneArt({ scene, className }: { scene: string; className?: string }) {
  const id = useId().replace(/:/g, "");
  const Scene = SCENES[scene] ?? Platform;
  return (
    <svg viewBox="0 0 100 60" preserveAspectRatio="xMidYMid slice" className={className} aria-hidden>
      <Defs id={id} />
      <Scene id={id} />
    </svg>
  );
}
