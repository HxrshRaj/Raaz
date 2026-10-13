import { useId } from "react";
import type { TPortrait } from "@/lib/schemas";

type Props = { portrait: TPortrait; mood?: string; className?: string; label?: string };

/** Original vector portrait generated from a character's look + current conversational mood. */
export function Portrait({ portrait: p, mood = "guarded", className, label }: Props) {
  const uid = useId().replace(/:/g, "");
  const tense = ["defensive", "cornered", "hostile"].includes(mood);
  const anxious = mood === "anxious" || mood === "cornered";
  const warm = ["open", "cooperative"].includes(mood);
  const browTilt = tense ? 5 : anxious ? -4 : 0;
  const mouth = warm ? "M82 150 Q100 162 118 150" : tense ? "M84 154 Q100 148 116 154" : anxious ? "M84 153 Q100 151 116 156" : "M85 153 Q100 156 115 153";
  const age = p.age === "old" ? 1 : p.age === "young" ? -1 : 0;
  const hair = p.hair;
  return (
    <svg viewBox="0 0 200 240" role="img" aria-label={label ?? `Portrait, mood ${mood}`} className={className}>
      <defs>
        <radialGradient id={`bg${uid}`} cx="30%" cy="20%" r="90%">
          <stop offset="0" stopColor="#f2a94e" stopOpacity="0.45" />
          <stop offset="0.45" stopColor="#1d2636" />
          <stop offset="1" stopColor="#090d14" />
        </radialGradient>
        <linearGradient id={`sk${uid}`} x1="0" x2="1">
          <stop offset="0" stopColor={p.skin} />
          <stop offset="1" stopColor={p.skin} stopOpacity="0.78" />
        </linearGradient>
        <linearGradient id={`sh${uid}`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.45" />
        </linearGradient>
      </defs>
      <rect width="200" height="240" fill={`url(#bg${uid})`} />
      {/* rain streaks behind */}
      {[18, 44, 150, 176, 190].map((x, i) => <line key={i} x1={x} y1={10 + i * 9} x2={x - 6} y2={46 + i * 9} stroke="#9fb4d1" strokeOpacity="0.2" />)}
      {/* shoulders / outfit */}
      <path d="M10 240 Q18 188 70 176 L130 176 Q182 188 190 240 Z" fill={p.outfit} />
      <path d="M70 176 L100 214 L130 176 Q100 168 70 176Z" fill={p.accent} fillOpacity="0.85" />
      <path d="M86 176 L100 200 L114 176" fill="none" stroke="#00000066" strokeWidth="2" />
      {/* neck */}
      <rect x="86" y="146" width="28" height="34" rx="8" fill={`url(#sk${uid})`} />
      <rect x="86" y="146" width="28" height="34" rx="8" fill="#000" fillOpacity="0.18" />
      {/* ears */}
      <ellipse cx="55" cy="112" rx="7" ry="12" fill={p.skin} />
      <ellipse cx="145" cy="112" rx="7" ry="12" fill={p.skin} />
      {/* hair back */}
      {p.hair_style === "long" && <path d="M48 110 Q40 190 62 200 L70 120 Z M152 110 Q160 190 138 200 L130 120 Z" fill={hair} />}
      {/* head */}
      <ellipse cx="100" cy="106" rx={46 - age} ry={56 + age} fill={`url(#sk${uid})`} />
      {/* beard */}
      {p.beard && <path d="M56 118 Q60 168 100 172 Q140 168 144 118 Q130 148 100 148 Q70 148 56 118Z" fill={hair} fillOpacity={age > 0 ? 0.65 : 0.9} />}
      {/* hair top */}
      {p.hair_style === "short" && <path d="M54 98 Q52 50 100 48 Q148 50 146 98 Q132 72 100 72 Q68 72 54 98Z" fill={hair} />}
      {p.hair_style === "long" && <path d="M52 100 Q50 46 100 46 Q150 46 148 100 Q134 66 100 66 Q64 66 52 100Z" fill={hair} />}
      {p.hair_style === "bun" && <><circle cx="100" cy="38" r="15" fill={hair} /><path d="M54 98 Q52 52 100 50 Q148 52 146 98 Q130 70 100 70 Q70 70 54 98Z" fill={hair} /></>}
      {p.hair_style === "cap" && <><path d="M52 92 Q54 44 100 42 Q146 44 148 92 Z" fill={p.outfit} /><rect x="46" y="88" width="108" height="9" rx="4" fill={p.accent} /><path d="M54 96 Q36 100 38 108 L62 100Z" fill={p.outfit} /></>}
      {age > 0 && p.hair_style !== "cap" && <path d="M56 100 Q58 78 70 70" stroke="#d8d8d8" strokeOpacity="0.5" strokeWidth="4" fill="none" />}
      {/* brows */}
      <g stroke="#1a1414" strokeWidth="4" strokeLinecap="round" strokeOpacity="0.85">
        <line x1="70" y1={96 + browTilt} x2="90" y2={96 - browTilt / 1.2} />
        <line x1="110" y1={96 - browTilt / 1.2} x2="130" y2={96 + browTilt} />
      </g>
      {/* eyes */}
      <g>
        <ellipse cx="80" cy="108" rx="8" ry={anxious ? 7 : 5} fill="#f4efe4" />
        <ellipse cx="120" cy="108" rx="8" ry={anxious ? 7 : 5} fill="#f4efe4" />
        <circle cx="82" cy="108" r="3.3" fill="#1a1414" />
        <circle cx="122" cy="108" r="3.3" fill="#1a1414" />
        <circle cx="83" cy="107" r="1" fill="#fff" />
        <circle cx="123" cy="107" r="1" fill="#fff" />
      </g>
      {p.glasses && <g fill="none" stroke={p.accent} strokeWidth="2.4"><rect x="66" y="99" width="28" height="20" rx="7" /><rect x="106" y="99" width="28" height="20" rx="7" /><line x1="94" y1="108" x2="106" y2="108" /></g>}
      {/* nose + mouth */}
      <path d="M100 112 Q94 130 102 134" stroke="#00000055" strokeWidth="2.4" fill="none" strokeLinecap="round" />
      <path d={mouth} stroke="#3a1a1a" strokeWidth="3" fill="none" strokeLinecap="round" />
      {p.age === "old" && <><path d="M62 122 Q70 128 78 124" stroke="#00000033" fill="none" /><path d="M122 124 Q130 128 138 122" stroke="#00000033" fill="none" /></>}
      {mood === "cornered" && <path d="M146 80 q4 8 0 12 q-4 -4 0 -12z" fill="#9fd0ff" fillOpacity="0.8" />}
      <rect width="200" height="240" fill={`url(#sh${uid})`} />
    </svg>
  );
}
