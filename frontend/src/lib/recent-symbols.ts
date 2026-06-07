const KEY = "vt:recent-symbols";
const MAX_RECENT = 20;

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function loadRecent(): string[] {
  const store = storage();
  if (!store) return [];
  try {
    const parsed = JSON.parse(store.getItem(KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((code) => typeof code === "string").slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

export function pushRecent(code: string): string[] {
  const normalized = code.trim();
  if (!normalized) return loadRecent();
  const next = [normalized, ...loadRecent().filter((item) => item !== normalized)].slice(0, MAX_RECENT);
  storage()?.setItem(KEY, JSON.stringify(next));
  return next;
}
