/** API client for LicenseLight backend. */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type { UploadResponse, AnalysisStatus, FontSearchResult } from "@/types";

export async function uploadImage(
  file: File,
  apiKey?: string,
  aiProvider?: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (apiKey) formData.append("api_key", apiKey);
  if (aiProvider) formData.append("ai_provider", aiProvider);

  const res = await fetch(`${API_URL}/api/v1/check/image`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function getAnalysisStatus(taskId: string): Promise<AnalysisStatus> {
  const res = await fetch(`${API_URL}/api/v1/check/status/${taskId}`);

  if (!res.ok) {
    throw new Error(`Failed to get status: ${res.status}`);
  }

  return res.json();
}

export async function searchFonts(query: string): Promise<FontSearchResult[]> {
  const res = await fetch(
    `${API_URL}/api/v1/fonts/search?q=${encodeURIComponent(query)}`
  );

  if (!res.ok) {
    return [];
  }

  return res.json();
}

export async function pollAnalysisStatus(
  taskId: string,
  onUpdate: (status: AnalysisStatus) => void,
  onComplete: (result: AnalysisStatus) => void,
  onError: (error: Error) => void,
  intervalMs: number = 2000
): Promise<() => void> {
  let cancelled = false;

  const poll = async () => {
    while (!cancelled) {
      try {
        const status = await getAnalysisStatus(taskId);
        onUpdate(status);

        if (status.status === "completed" || status.status === "failed") {
          onComplete(status);
          return;
        }
      } catch (err) {
        if (!cancelled) {
          onError(err instanceof Error ? err : new Error("Polling failed"));
        }
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  };

  poll();

  return () => {
    cancelled = true;
  };
}
