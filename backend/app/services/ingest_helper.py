import io
import os
import asyncio
import json
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlparse
from mistralai import Mistral
import PyPDF2
import docx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import numpy as np
from numpy.linalg import norm


def split_text(content: str, chunk_size: int=1024, overlap: int=128) -> List[Tuple[str, int, int]]:
    chunks, start, L = ([], 0, len(content))
    if chunk_size <= 0:
        chunk_size = 1024
    if overlap < 0:
        overlap = 0
    while start < L:
        end = min(start + chunk_size, L)
        chunks.append((content[start:end], start, end))
        if end == L:
            return chunks
        start = max(end - overlap, start + 1)
    return chunks

def parse_bytes_by_ext(data: bytes, ext: str) -> str:
    ext = ext.lower()
    if ext in ['.txt', '.md']:
        return data.decode('utf-8', errors='ignore')
    if ext == '.pdf':
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        out = []
        for p in reader.pages:
            t = p.extract_text() or ''
            out.append(t)
        return '\n'.join(out)
    elif ext == '.docx':
        d = docx.Document(io.BytesIO(data))
        return '\n'.join([p.text for p in d.paragraphs])
    else:
        if ext == '.html':
            soup = BeautifulSoup(data.decode('utf-8', errors='ignore'), 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        raise ValueError(f'Format non supporté: {ext}')

async def add_context_to_chunks(chunks: List[Tuple[str, int, int]], document_text: str, model: str = 'mistral-large-latest', timeout_s: float = 30.0, concurrency: int = 8) -> List[Tuple[str, int, int]]:
    if len(document_text) > 700000:
        document_text = document_text[:700000]

    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        raise ValueError('MISTRAL_API_KEY environment variable is required')
    
    client = Mistral(api_key=api_key)
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(c: Tuple[str, int, int]) -> Tuple[str, int, int]:
        chunk_text = c[0]
        messages = [
            {'role': 'system', 'content': 'You are a retrieval assistant. Given a chunk from the user, return a concise 1-4 sentence context label that situates the chunk within the cached document. Be specific, no fluff. YOU MUST USE THE SAME LANGUAGE AS THE DOCUMENT.'},
            {'role': 'user', 'content': f'\n<document>\n{document_text}\n</document>\n<chunk>\n{chunk_text}\n</chunk>\nGive only the succinct context (same language as the document).\nYOU MUST USE THE SAME LANGUAGE AS THE DOCUMENT.'}
        ]
        async with sem:
            loop = asyncio.get_event_loop()
            r = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.chat.complete(
                        model=model,
                        messages=messages,
                        temperature=0.75,
                        max_tokens=256
                    )
                ),
                timeout=timeout_s
            )
        ctx = (r.choices[0].message.content or '').strip()
        return (f'{ctx} {chunk_text}'.strip(), c[1], c[2])

    return await asyncio.gather(*[one(chunk) for chunk in chunks])

def normalize_embedding(embedding: List[float]) -> List[float]:
    embedding_array = np.array(embedding)
    normalized = embedding_array / np.linalg.norm(embedding_array)
    return normalized.tolist()

def embed_texts(
    batch: List[str],
    model: str='models/gemini-embedding-001',
    task_type: str='retrieval_document'
) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts using Gemini

    Args:
        batch: List of texts to embed (max 100)
        model: Gemini embedding model to use (default: models/gemini-embedding-001)
        task_type: Type of task ('retrieval_document', 'retrieval_query', 'clustering', 'classification')

    Returns:
        List of normalized embedding vectors (1536 dimensions)
    """
    if len(batch) == 0 or len(batch) > 100:
        raise ValueError('Batch size must be between 1 and 100')

    valid_task_types = ['retrieval_document', 'retrieval_query', 'semantic_similarity', 'classification', 'clustering']
    if task_type not in valid_task_types:
        raise ValueError(f'Invalid task_type. Must be one of: {valid_task_types}')

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('GEMINI_API_KEY environment variable is required')

    client = genai.Client(api_key=api_key)

    # Truncate each text to 2048 tokens (Gemini limit)
    truncated_batch = [text[:2048] for text in batch]

    resp = client.models.embed_content(
        model=model,
        contents=truncated_batch,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=1536
        )
    )
    embs = [normalize_embedding(d.values) for d in resp.embeddings]
    return embs

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        if end >= text_length:
            chunks.append(text[start:].strip())
            break
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block
        elif '\n\n' in chunk:
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:
                end = start + last_break
        elif '. ' in chunk:
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:
                end = start + last_period + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = max(start + 1, end)
    return chunks

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        raise ValueError('MISTRAL_API_KEY environment variable is required')
    
    client = Mistral(api_key=api_key)
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.complete(
                model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}
                ],
                response_format={"type": "json_object"}
            )
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str) -> List[float]:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('GEMINI_API_KEY environment variable is required')

    client = genai.Client(api_key=api_key)
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=[text[:2048]],  # Gemini embedding max 2048 tokens
                config=types.EmbedContentConfig(
                    task_type="retrieval_document",
                    output_dimensionality=1536
                )
            )
        )
        embedding = response.embeddings[0].values
        return normalize_embedding(embedding)
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536