export type PromptHandoff = {
  rawInput: string;
  description: string;
  interventionType: string | null;
  location: string | null;
  parameters: Record<string, unknown>;
};

const KEY_PREFIX = "matrix:prompt:";

function key(scenarioId: string): string {
  return `${KEY_PREFIX}${scenarioId}`;
}

function isPromptHandoff(value: unknown): value is PromptHandoff {
  if (value === null || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.rawInput === "string" &&
    typeof v.description === "string" &&
    (v.interventionType === null || typeof v.interventionType === "string") &&
    (v.location === null || typeof v.location === "string") &&
    typeof v.parameters === "object" &&
    v.parameters !== null &&
    !Array.isArray(v.parameters)
  );
}

export function savePromptHandoff(scenarioId: string, payload: PromptHandoff): void {
  if (typeof sessionStorage === "undefined" || !scenarioId) return;
  try {
    sessionStorage.setItem(key(scenarioId), JSON.stringify(payload));
  } catch {
    // Quota / private mode — first paint falls back to GET /scenario.
  }
}

export function takePromptHandoff(scenarioId: string): PromptHandoff | null {
  if (typeof sessionStorage === "undefined" || !scenarioId) return null;
  try {
    const raw = sessionStorage.getItem(key(scenarioId));
    if (!raw) return null;
    sessionStorage.removeItem(key(scenarioId));
    const parsed: unknown = JSON.parse(raw);
    return isPromptHandoff(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
