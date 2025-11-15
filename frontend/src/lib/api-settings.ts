const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface AISettings {
  id: string;
  user_id: string;
  model_name: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  created_at: string;
  updated_at: string;
}

export async function getAISettings(): Promise<AISettings> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ai-settings/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function updateAISettings(settings: Partial<AISettings>): Promise<AISettings> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ai-settings/`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function patchAISettings(settings: Partial<AISettings>): Promise<AISettings> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ai-settings/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}
