/** Client-side API key persistence (localStorage). Keys are never sent to the server except during analysis. */

import type { AIProvider, UserSettings } from "@/types";

const SETTINGS_KEY = "licenselight-settings";

export function getSettings(): UserSettings | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.apiKey && parsed?.aiProvider) {
      return parsed as UserSettings;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveSettings(settings: UserSettings): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function clearSettings(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SETTINGS_KEY);
}

/** Show only first 3 + last 4 characters, middle masked. E.g. "sk-***b123" */
export function maskApiKey(key: string): string {
  if (key.length <= 10) return key.slice(0, 3) + "***";
  return key.slice(0, 3) + "***" + key.slice(-4);
}

/** Human-readable provider label */
export function getProviderLabel(provider: AIProvider | string): string {
  const labels: Record<string, string> = {
    claude: "Claude (Anthropic)",
    openai: "OpenAI (GPT-4o)",
    deepseek: "DeepSeek",
    gemini: "Gemini (Google)",
    kimi: "Kimi (Moonshot)",
  };
  return labels[provider] || provider;
}

/** Whether the provider supports image/vision analysis */
export function providerHasVision(provider: AIProvider | string): boolean {
  return ["claude", "openai", "gemini", "kimi"].includes(provider);
}
