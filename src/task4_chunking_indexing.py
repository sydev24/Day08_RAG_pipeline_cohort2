"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (Weaviate khuyến cáo)

Chunking options (langchain-text-splitters):
    - RecursiveCharacterTextSplitter: an toàn, phổ biến
    - MarkdownHeaderTextSplitter: tốt cho file có heading
    - SemanticChunker: dùng embedding để tách (nâng cao)

Embedding model options:
    - sentence-transformers/all-MiniLM-L6-v2 (384 dim, nhẹ)
    - BAAI/bge-m3 (1024 dim, multilingual, tốt cho tiếng Việt)
    - OpenAI text-embedding-3-small (1536 dim, API)

Vector store options:
    - Weaviate (khuyến cáo: hỗ trợ hybrid search built-in)
    - ChromaDB (đơn giản, local)
    - FAISS (chỉ dense search)

Cài đặt:
    pip install langchain-text-splitters sentence-transformers weaviate-client
"""

from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# CHUNKING_METHOD = "recursive": Sử dụng bộ phân tách đệ quy để giữ nguyên vẹn cấu trúc các đoạn văn/điều khoản
CHUNKING_METHOD = "recursive"  # "recursive" | "markdown_header" | "semantic"

# EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2":
# Mô hình đa ngôn ngữ gọn nhẹ (~420MB), tải nhanh, xử lý local bằng CPU không bị giới hạn quota API.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# CHUNK_SIZE = 600: Kích thước tối ưu cho mô hình local SBERT để tránh bị mất/cắt thông tin 
# do giới hạn độ dài context token (max sequence length 128/256).
CHUNK_SIZE = 600

# CHUNK_OVERLAP = 60: Giữ ngữ cảnh liên kết khoảng 10 từ giữa các chunk liền kề.
CHUNK_OVERLAP = 60

# VECTOR_STORE = "json_local": Sử dụng lưu trữ file JSON cục bộ vì Weaviate Embedded 
# không hỗ trợ hệ điều hành Windows (chỉ hỗ trợ Linux/macOS).
VECTOR_STORE = "json_local"  # "json_local" | "weaviate"

    
# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
   
    documents = []
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            doc_type = "legal" if "legal" in str(md_file) else "news"
            documents.append({
                "content": content,
                "metadata": {"source": md_file.name, "type": doc_type}
            })
        except Exception as e:
            print(f"[!] Error reading file {md_file.name}: {e}")    
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    #
    # Ví dụ với RecursiveCharacterTextSplitter:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    #
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "content": chunk_text,
                "metadata": {**doc["metadata"], "chunk_index": i}
            })
    return chunks

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    if "models/" in EMBEDDING_MODEL:
        import os
        import google.generativeai as genai
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY") # dự phòng nếu dùng key chung
        if not api_key:
            raise ValueError("Vui lòng cấu hình GEMINI_API_KEY hoặc GOOGLE_API_KEY trong file .env để sử dụng Gemini API")
        
        genai.configure(api_key=api_key)
        texts = [c["content"] for c in chunks]
        print(f"[i] Dang embed {len(texts)} chunks bang Gemini API...")
        
        embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch_texts,
                task_type="retrieval_document"
            )
            embeddings.extend(result['embedding'])
            
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb
        return chunks
    else:
        # Ví dụ với sentence-transformers:
        from sentence_transformers import SentenceTransformer
        #
        model = SentenceTransformer(EMBEDDING_MODEL)
        texts = [c["content"] for c in chunks]
        print(f"[i] Dang embed {len(texts)} chunks...")
        embeddings = model.encode(texts, show_progress_bar=True)
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb.tolist()
        return chunks


def save_to_json(chunks: list[dict]):
    vector_store_path = STANDARDIZED_DIR.parent / "vector_store.json"
    print(f"[i] Dang luu {len(chunks)} chunks vao file JSON: {vector_store_path}...")
    import json
    with open(vector_store_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4)
    print("[OK] Luu file JSON hoan tat.")


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn.
    """
    if VECTOR_STORE == "json_local":
        save_to_json(chunks)
        return

    try:
        import weaviate
        from weaviate.classes.config import Configure, Property, DataType
        
        print(f"[i] Dang ket noi toi Weaviate Embedded...")
        client = weaviate.connect_to_embedded(persistence_data_path="data/weaviate_db")
        
        try:
            collection_name = "DrugLawDocs"
            if client.collections.exists(collection_name):
                print(f"[i] Da ton tai collection '{collection_name}', dang xoa de lam sach...")
                client.collections.delete(collection_name)
                
            collection = client.collections.create(
                name=collection_name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="doc_type", data_type=DataType.TEXT),
                    Property(name="chunk_index", data_type=DataType.INT),
                ]
            )
            
            print(f"[i] Dang nap {len(chunks)} chunks vao Weaviate...")
            with collection.batch.dynamic() as batch:
                for chunk in chunks:
                    batch.add_object(
                        properties={
                            "content": chunk["content"],
                            "source": chunk["metadata"]["source"],
                            "doc_type": chunk["metadata"]["type"],
                            "chunk_index": chunk["metadata"]["chunk_index"]
                        },
                        vector=chunk["embedding"]
                    )
            print("[OK] Hoan thanh nap du lieu vao Weaviate.")
        finally:
            client.close()
            
    except Exception as e:
        print(f"[!] Khong the khoi dong Weaviate Embedded (co the do khong ho tro Windows): {e}")
        print("[i] Tu dong chuyen sang luu tru JSON cuc bo...")
        save_to_json(chunks)


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n[OK] Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"[OK] Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"[OK] Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("[OK] Indexed to vector store")


if __name__ == "__main__":
    run_pipeline()
