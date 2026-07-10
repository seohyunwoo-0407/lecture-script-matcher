export type ThemeId =
  | "classic"
  | "sage"
  | "apple"
  | "library"
  | "pastel"
  | "ice";

export type TextSizeId = "sm" | "base" | "lg";

export interface ThemePreset {
  id: ThemeId;
  label: string;
  background: string;
  text: string;
  tileBorder?: string;
}

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: "classic",
    label: "Classic note",
    background: "#ffffff",
    text: "#1e293b",
    tileBorder: "#e2e8f0",
  },
  {
    id: "sage",
    label: "Sage study",
    background: "#f0fdf4",
    text: "#14532d",
    tileBorder: "#bbf7d0",
  },
  {
    id: "apple",
    label: "Apple",
    background: "#ffffff",
    text: "#374151",
    tileBorder: "#e5e7eb",
  },
  {
    id: "library",
    label: "Library",
    background: "#faf8f3",
    text: "#334155",
    tileBorder: "#e7e5e0",
  },
  {
    id: "pastel",
    label: "Pastel",
    background: "#fdf2f8",
    text: "#6b21a8",
    tileBorder: "#f5d0fe",
  },
  {
    id: "ice",
    label: "Ice",
    background: "#f0f9ff",
    text: "#1e3a8a",
    tileBorder: "#bae6fd",
  },
];

export const TEXT_SIZE_OPTIONS: {
  id: TextSizeId;
  label: string;
  previewClass: string;
}[] = [
  { id: "lg", label: "Large", previewClass: "text-lg" },
  { id: "base", label: "medium", previewClass: "text-base" },
  { id: "sm", label: "small", previewClass: "text-sm" },
];

export function getThemeById(id: ThemeId): ThemePreset {
  return THEME_PRESETS.find((t) => t.id === id) ?? THEME_PRESETS[0];
}
