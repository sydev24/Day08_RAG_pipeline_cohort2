"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""
import sys
from pathlib import Path
# Thêm thư mục cha (Project Root) vào danh sách đường dẫn tìm kiếm của Python
sys.path.append(str(Path(__file__).parent.parent))

# (Sau đó mới thực hiện import này)
from src.task4_chunking_indexing import EMBEDDING_MODEL

import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

# Import cấu hình tên model trực tiếp từ Task 4 để tránh bị lệch model
from src.task4_chunking_indexing import EMBEDDING_MODEL

# Đường dẫn tới file vector store đã lưu ở Task 4
VECTOR_STORE_PATH = Path(__file__).parent.parent / "data" / "vector_store.json"

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Tính độ tương đồng cosine giữa 2 vector.
    """
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
        
    return float(dot_product / (norm_vec1 * norm_vec2))

def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity từ json_local.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
   
    # Bước 1: Embed query bằng cùng model ở Task 4
    if not VECTOR_STORE_PATH.exists():
        print(f"[!] File vector store khong ton tai tai: {VECTOR_STORE_PATH}")
        return []
        
    with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    if not corpus:
        return []
        
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = model.encode(query).tolist()
    # Bước 2: Query vector store (cosine similarity)
    results = []
    for chunk in corpus:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        results.append({
            "content": chunk["content"],
            "score": score,
            "metadata": chunk["metadata"]
        })
    # Bước 3: Return top_k results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]   

if __name__ == "__main__":
    # Test
    results = semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
