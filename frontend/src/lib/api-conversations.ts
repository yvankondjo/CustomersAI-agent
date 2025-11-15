const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface ConversationMessage {
  id: string;
  role: string;
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  platform: string;
  platform_user_id?: string;
  platform_username?: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_message?: string;
  unread_count: number;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: ConversationMessage[];
}

export async function getConversations(
  platform?: string,
  status?: string,
  limit: number = 50
): Promise<Conversation[]> {
  const params = new URLSearchParams();
  
  if (platform && platform !== "all") {
    params.append("platform", platform);
  }
  
  if (status && status !== "all") {
    params.append("status", status);
  }
  
  params.append("limit", limit.toString());

  const response = await fetch(
    `${API_BASE_URL}/api/v1/conversations?${params.toString()}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getConversationDetail(conversationId: string): Promise<ConversationDetail> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function replyToConversation(
  conversationId: string,
  content: string
): Promise<{ status: string; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}/reply`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function updateConversationStatus(
  conversationId: string,
  status: "active" | "resolved" | "escalated"
): Promise<{ status: string; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}/status`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return `${diffInSeconds}s ago`;
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) {
    return `${diffInDays}d ago`;
  }

  return date.toLocaleDateString();
}

export function getChannelDisplayName(platform: string): string {
  switch (platform.toLowerCase()) {
    case "instagram":
      return "Instagram";
    case "whatsapp":
      return "WhatsApp";
    case "website":
      return "Website";
    case "web":
      return "Website";
    case "playground":
      return "Website";
    default:
      return platform.charAt(0).toUpperCase() + platform.slice(1);
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800";
    case "resolved":
      return "bg-gray-100 text-gray-800";
    case "escalated":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}
