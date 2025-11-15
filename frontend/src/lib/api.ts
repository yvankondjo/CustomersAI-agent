const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface DocumentIngestRequest {
  document_id: string;
}

export interface WebsiteIngestRequest {
  url: string;
  max_pages?: number;
  website_page_id?: string;
}

export interface IngestionResponse {
  status: string;
  job_id: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "started" | "finished" | "failed";
  result?: any;
  error?: string;
  created_at?: string;
  started_at?: string;
  ended_at?: string;
}

export async function ingestDocument(data: DocumentIngestRequest): Promise<IngestionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/document`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to queue document ingestion");
  }

  return response.json();
}

export async function ingestWebsite(data: WebsiteIngestRequest): Promise<IngestionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/website`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to queue website ingestion");
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/job/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch job status");
  }

  return response.json();
}

export interface Document {
  id: string;
  filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  status: "pending" | "processing" | "processed" | "failed";
  chunk_count?: number;
  metadata?: any;
  created_at: string;
  updated_at?: string;
}

export interface Website {
  base_url: string;
  pages: WebsitePage[];
  total_pages: number;
  total_chunks: number;
}

export interface WebsitePage {
  id: string;
  website_source_id?: string;
  url: string;
  title?: string;
  content?: string;
  metadata?: any;
  chunk_count?: number;
  crawled_at?: string;
  created_at: string;
}

export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch documents");
  }

  return response.json();
}

export async function listWebsites(): Promise<Website[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/websites`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch websites");
  }

  return response.json();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents/${documentId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete document");
  }
}

export async function deleteWebsite(websiteId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/websites/${websiteId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete website");
  }
}

