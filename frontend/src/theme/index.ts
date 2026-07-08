import { updatePrimaryPalette } from '@primeuix/themes'

/**
 * Studio-wide appearance. Chosen by the studio admin (server-persisted on the
 * tenant) and applied for every user of the studio — staff and members alike.
 *
 * Unlike the locale (a per-browser preference), the theme is NOT read from
 * localStorage: it comes from the server via `/auth/me` and is applied on app
 * start and after login. localStorage is only used as a paint-flash guard so
 * the correct colours show before the network round-trip completes.
 */

export const SUPPORTED_THEME_PRESETS = [
  'emerald',
  'blue',
  'violet',
  'amber',
  'rose',
  'teal',
  'indigo',
] as const

export type ThemePreset = (typeof SUPPORTED_THEME_PRESETS)[number]

export const SUPPORTED_THEME_MODES = ['light', 'dark'] as const
export type ThemeMode = (typeof SUPPORTED_THEME_MODES)[number]

export const DEFAULT_PRESET: ThemePreset = 'emerald'
export const DEFAULT_MODE: ThemeMode = 'light'

const PRESET_KEY = 'studio-os.theme.preset'
const MODE_KEY = 'studio-os.theme.mode'

/**
 * 50–950 colour ramps per accent. Values mirror the Tailwind palettes so they
 * blend naturally with the Aura preset's neutral surfaces.
 */
const PALETTES: Record<ThemePreset, Record<string, string>> = {
  emerald: {
    50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0', 300: '#6ee7b7',
    400: '#34d399', 500: '#10b981', 600: '#059669', 700: '#047857',
    800: '#065f46', 900: '#064e3b', 950: '#022c22',
  },
  blue: {
    50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd',
    400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8',
    800: '#1e40af', 900: '#1e3a8a', 950: '#172554',
  },
  violet: {
    50: '#f5f3ff', 100: '#ede9fe', 200: '#ddd6fe', 300: '#c4b5fd',
    400: '#a78bfa', 500: '#8b5cf6', 600: '#7c3aed', 700: '#6d28d9',
    800: '#5b21b6', 900: '#4c1d95', 950: '#2e1065',
  },
  amber: {
    50: '#fffbeb', 100: '#fef3c7', 200: '#fde68a', 300: '#fcd34d',
    400: '#fbbf24', 500: '#f59e0b', 600: '#d97706', 700: '#b45309',
    800: '#92400e', 900: '#78350f', 950: '#451a03',
  },
  rose: {
    50: '#fff1f2', 100: '#ffe4e6', 200: '#fecdd3', 300: '#fda4af',
    400: '#fb7185', 500: '#f43f5e', 600: '#e11d48', 700: '#be123c',
    800: '#9f1239', 900: '#881337', 950: '#4c0519',
  },
  teal: {
    50: '#f0fdfa', 100: '#ccfbf1', 200: '#99f6e4', 300: '#5eead4',
    400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e',
    800: '#115e59', 900: '#134e4a', 950: '#042f2e',
  },
  indigo: {
    50: '#eef2ff', 100: '#e0e7ff', 200: '#c7d2fe', 300: '#a5b4fc',
    400: '#818cf8', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca',
    800: '#3730a3', 900: '#312e81', 950: '#1e1b4b',
  },
}

/** Representative swatch colour (500 shade) for UI previews. */
export function presetColor(preset: ThemePreset): string {
  return PALETTES[preset]?.[500] ?? PALETTES[DEFAULT_PRESET][500]
}

function isPreset(value: string | null): value is ThemePreset {
  return (
    value !== null &&
    (SUPPORTED_THEME_PRESETS as readonly string[]).includes(value)
  )
}

function isMode(value: string | null): value is ThemeMode {
  return (
    value !== null && (SUPPORTED_THEME_MODES as readonly string[]).includes(value)
  )
}

/** Applies the theme to the running app (PrimeVue palette + dark-mode class). */
export function applyTheme(preset: ThemePreset, mode: ThemeMode): void {
  updatePrimaryPalette(PALETTES[preset] ?? PALETTES[DEFAULT_PRESET])
  document.documentElement.classList.toggle('app-dark', mode === 'dark')
  localStorage.setItem(PRESET_KEY, preset)
  localStorage.setItem(MODE_KEY, mode)
}

/** The last-applied theme cached in localStorage, for a flash-free first paint. */
export function cachedTheme(): { preset: ThemePreset; mode: ThemeMode } {
  const preset = localStorage.getItem(PRESET_KEY)
  const mode = localStorage.getItem(MODE_KEY)
  return {
    preset: isPreset(preset) ? preset : DEFAULT_PRESET,
    mode: isMode(mode) ? mode : DEFAULT_MODE,
  }
}
