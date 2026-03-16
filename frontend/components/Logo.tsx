"use client";

interface LogoProps {
  size?: number;
}

export function Logo({ size = 32 }: LogoProps) {
  const s = size;
  const r = Math.round(s * 0.25); // border radius

  return (
    <svg
      width={s}
      height={s}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="logo-bg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#4F46E5" />
        </linearGradient>
        <linearGradient id="logo-wave" x1="0" y1="0" x2="20" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="rgba(255,255,255,0.55)" />
          <stop offset="100%" stopColor="rgba(255,255,255,1)" />
        </linearGradient>
        <clipPath id="logo-clip">
          <rect width="32" height="32" rx="7" />
        </clipPath>
      </defs>

      {/* Background with gradient */}
      <rect width="32" height="32" rx="7" fill="url(#logo-bg)" />

      {/* Subtle inner highlight */}
      <rect width="32" height="16" rx="7" fill="rgba(255,255,255,0.06)" clipPath="url(#logo-clip)" />

      {/* Left vertical bar of H */}
      <rect x="6" y="7" width="4" height="18" rx="1.5" fill="white" />

      {/* Right vertical bar of H */}
      <rect x="22" y="7" width="4" height="18" rx="1.5" fill="white" />

      {/* Waveform crossbar — replaces the flat horizontal bar */}
      {/* The wave goes from left bar to right bar at mid-height (y≈15.5) */}
      {/* Left half: slightly jagged/synthetic (AI side) */}
      {/* Right half: smooth organic curve (human side) */}
      <path
        d="M10 15.5 L12 13 L13.5 17.5 L15 14 L16 15.5 Q17.5 13 19 15.5 Q20.5 18 22 15.5"
        stroke="url(#logo-wave)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}