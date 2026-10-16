"""
Day 3 Lab Solution: Build the Document Ingestion Pipeline

Full pipeline: Textract extraction -> chunking -> Bedrock embeddings -> OpenSearch indexing.
"""

import boto3
import time
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

REGION = "us-east-1"
OPENSEARCH_ENDPOINT = "your-opensearch-endpoint"
INDEX_NAME = "documents"

# Sentence Transformers, not Bedrock Titan — Bedrock's embedding models
# (Titan and Cohere) are denied in this environment. This must be the same
# model used everywhere else this week that queries this same index (the
# Retrieval Agent lesson and lab), since a different model would produce
# vectors of the wrong dimension.

_embed_model = None

def _get_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def create_index(client):
    index_body = {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "content": {"type": "text"},
                "source": {"type": "keyword"},
                "chunk_number": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "method": {"name": "hnsw", "space_type": "innerproduct", "engine": "faiss"}
                }
            }
        }
    }
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=index_body)
        print(f"Created index '{INDEX_NAME}'")
    else:
        print(f"Index '{INDEX_NAME}' already exists")


def get_opensearch_client():
    credentials = boto3.Session().get_credentials()
    auth = AWS4Auth(credentials.access_key, credentials.secret_key, REGION, "es", session_token=credentials.token)
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection
    )


def extract_text_from_s3_pdf(bucket: str, document_key: str) -> str:
    """
    Extracts text from a PDF stored in S3 using Textract's asynchronous API.

    NOTE: Textract's synchronous detect_document_text only supports
    single-page PDF/TIFF documents — a hard limit, not just a slower path.
    Real policy documents, case studies, and reports are frequently
    multiple pages, so a synchronous call fails outright on realistic
    input. Multi-page PDFs require the asynchronous start/get pattern
    below (confirmed against AWS's own Textract documentation).
    """
    textract = boto3.client("textract", region_name=REGION)

    start_response = textract.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": document_key}}
    )
    job_id = start_response["JobId"]

    # Poll until the job finishes. A basic timeout guards against an
    # unexpected stuck job rather than polling forever.
    max_attempts = 60  # ~2 minutes at 2s intervals; adjust for larger documents
    for _ in range(max_attempts):
        response = textract.get_document_text_detection(JobId=job_id)
        status = response["JobStatus"]
        if status in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(2)
    else:
        raise TimeoutError(f"Textract job {job_id} for {document_key} did not finish in time")

    if status == "FAILED":
        raise RuntimeError(
            f"Textract job failed for {document_key}: {response.get('StatusMessage', 'no message')}"
        )

    # Results can be paginated across multiple response pages for longer documents
    lines = [block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"]
    next_token = response.get("NextToken")
    while next_token:
        response = textract.get_document_text_detection(JobId=job_id, NextToken=next_token)
        lines.extend(block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE")
        next_token = response.get("NextToken")

    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[str]) -> list[dict]:
    model = _get_model()
    vectors = model.encode(chunks).tolist()
    return [{"content": chunk, "embedding": vec} for chunk, vec in zip(chunks, vectors)]


def index_chunks(embedded_chunks: list[dict], source_document: str, client):
    for i, chunk in enumerate(embedded_chunks):
        client.index(
            index=INDEX_NAME,
            id=f"{source_document}-{i}",
            body={
                "content": chunk["content"],
                "embedding": chunk["embedding"],
                "source": source_document,
                "chunk_number": i
            }
        )


def process_document(bucket: str, document_key: str, os_client):
    raw_text = extract_text_from_s3_pdf(bucket, document_key)
    chunks = chunk_text(raw_text, chunk_size=200, overlap=50)
    embedded_chunks = embed_chunks(chunks)
    index_chunks(embedded_chunks, document_key, os_client)
    print(f"Processed {len(chunks)} chunks from {document_key}")
    return len(chunks)


def get_embedding(text: str) -> list[float]:
    model = _get_model()
    return model.encode([text])[0].tolist()


def test_search(query: str, os_client, k: int = 3):
    vec = get_embedding(query)
    results = os_client.search(
        index=INDEX_NAME,
        body={"size": k, "query": {"knn": {"embedding": {"vector": vec, "k": k}}}}
    )
    print(f"\nQuery: {query}")
    for hit in results["hits"]["hits"]:
        print(f"  [{hit['_source']['source']}] score={hit['_score']:.3f}")
        print(f"    {hit['_source']['content'][:150]}...")


if __name__ == "__main__":
    os_client = get_opensearch_client()
    create_index(os_client)

    bucket = "your-unique-bucket-name-docs"
    sample_documents = [
        "remote-work-policy.pdf",
        "retail-supply-chain-case-study.pdf",
        "q2-2026-client-report.pdf",
        "cloud-migration-playbook.pdf",
    ]

    for doc in sample_documents:
        process_document(bucket, doc, os_client)

    print(f"\nTotal indexed: {os_client.count(index=INDEX_NAME)}")

    test_search("How much can employees claim for home office equipment?", os_client)
    test_search("What caused the reduction in food waste for the grocery client?", os_client)
    test_search("What data quality risk is affecting the migration timeline?", os_client)
    test_search("What are common pitfalls in a cloud data migration?", os_client)