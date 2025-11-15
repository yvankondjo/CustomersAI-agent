const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface PlaygroundMessage {
  content: string;
  conversation_id?: string;
}

export interface PlaygroundResponse {
  response: string;
  conversation_id: string;
}

export async function sendPlaygroundMessage(data: PlaygroundMessage): Promise<PlaygroundResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/playground/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to send message");
  }

  return response.json();
}

