const DEFAULT_API_BASE_URL = "http://localhost:8000";

function cleanBaseUrl(value: string | undefined): string {
  const baseUrl = value?.trim() || DEFAULT_API_BASE_URL;
  return baseUrl.replace(/\/+$/, "");
}

export const API_BASE_URL = cleanBaseUrl(process.env.NEXT_PUBLIC_API_URL);
export const ADMIN_TOKEN = process.env.ADMIN_TOKEN ?? "";
