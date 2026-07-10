const AMBIENT_ACCENT_MAP = {
  general: "hsl(220 22% 42%)",
  "neo-noir": "hsl(258 35% 38%)",
  documentary: "hsl(145 28% 36%)",
  horror: "hsl(0 42% 34%)",
  comedy: "hsl(42 55% 42%)",
  "sci-fi": "hsl(195 45% 38%)",
  "1970s": "hsl(32 58% 42%)",
  "1980s": "hsl(280 38% 40%)",
  "1990s": "hsl(210 40% 38%)",
  family: "hsl(168 32% 38%)",
};

const NEUTRAL_ACCENT = "hsl(220 14% 28%)";

export function resolveAmbientAccent(contextHash) {
  const key = String(contextHash || "general")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
  return AMBIENT_ACCENT_MAP[key] || NEUTRAL_ACCENT;
}

export function blendAmbientAccent(contextHash, personaAccent) {
  const contextAccent = resolveAmbientAccent(contextHash);
  if (!personaAccent) return contextAccent;
  return `color-mix(in srgb, ${contextAccent} 68%, ${personaAccent} 32%)`;
}
