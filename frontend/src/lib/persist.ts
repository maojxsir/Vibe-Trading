// Tiny localStorage helpers for user-editable, persisted page data.
// All keys are namespaced under "vt-" to avoid clashes with other app state.

const PREFIX = "vt-";

export function loadPersisted<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (raw) return JSON.parse(raw) as T;
  } catch {
    /* ignore corrupt cache */
  }
  return fallback;
}

export function savePersisted<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* ignore quota / serialization errors */
  }
}

export function clearPersisted(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key);
  } catch {
    /* ignore */
  }
}
