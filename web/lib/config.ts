const DEFAULT_API_BASE_URL = "/api";

function cleanBaseUrl(value: string | undefined): string {
  const baseUrl = value?.trim() || DEFAULT_API_BASE_URL;
  if (baseUrl === "/") return "";
  return baseUrl.replace(/\/+$/, "");
}

export const API_BASE_URL = cleanBaseUrl(process.env.NEXT_PUBLIC_API_URL);
