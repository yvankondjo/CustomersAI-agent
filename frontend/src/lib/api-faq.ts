const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface FAQ {
  id: string;
  question: string;
  variants: string[];
  answer: string;
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface FAQCreate {
  question: string;
  variants?: string[];
  answer: string;
  category?: string;
}

export interface FAQUpdate {
  question?: string;
  variants?: string[];
  answer?: string;
  category?: string;
}

export async function createFAQ(data: FAQCreate): Promise<FAQ> {
  const response = await fetch(`${API_BASE_URL}/api/v1/faq`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create FAQ");
  }

  return response.json();
}

export async function listFAQs(): Promise<FAQ[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/faq`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to list FAQs");
  }

  return response.json();
}

export async function getFAQ(id: string): Promise<FAQ> {
  const response = await fetch(`${API_BASE_URL}/api/v1/faq/${id}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get FAQ");
  }

  return response.json();
}

export async function updateFAQ(id: string, data: FAQUpdate): Promise<FAQ> {
  const response = await fetch(`${API_BASE_URL}/api/v1/faq/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update FAQ");
  }

  return response.json();
}

export async function deleteFAQ(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/faq/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete FAQ");
  }
}

