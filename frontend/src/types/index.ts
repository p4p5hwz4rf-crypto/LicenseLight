/** Type definitions for LicenseLight frontend. */

export interface FontResult {
  name: string;
  risk: "green" | "yellow" | "red";
  explanation: string;
  alternatives: string[];
}

export interface ImageSourceResult {
  source_url: string;
  risk: "green" | "yellow" | "red";
  explanation: string;
  alternatives: string[];
}

export interface AnalysisReport {
  overall_risk: "green" | "yellow" | "red";
  fonts: FontResult[];
  image_source: ImageSourceResult | null;
  summary: string;
}

export interface AnalysisStatus {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_message: string | null;
  result: AnalysisReport | null;
  created_at: string;
  completed_at: string | null;
}

export interface UploadResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface FontSearchResult {
  font: {
    id: number;
    name: string;
    foundry: string | null;
    license_type: string | null;
    commercial_use: boolean | null;
    requires_attribution: boolean | null;
    embedding_allowed: boolean | null;
    web_font_allowed: boolean | null;
    price_info: string | null;
    official_url: string | null;
  };
  match_type: string;
  score: number;
}
