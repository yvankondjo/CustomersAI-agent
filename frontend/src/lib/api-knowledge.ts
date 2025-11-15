const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Document {
  id: string;
  filename: string;
  file_path?: string;
  file_size?: number;
  mime_type?: string;
  status: string;
  chunk_count?: number;
  created_at: string;
}

export interface Website {
  base_url: string;
  pages: Array<{
    id: string;
    url: string;
    title?: string;
    chunk_count?: number;
    created_at: string;
  }>;
  total_pages: number;
  total_chunks: number;
}

export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to list documents");
  }

  return response.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete document");
  }
}

export async function listWebsites(): Promise<Website[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/websites`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to list websites");
  }

  return response.json();
}

export async function deleteAllWebsites(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/websites/all`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete all websites");
  }
}

export async function deleteWebsite(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/websites/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete website");
  }
}

