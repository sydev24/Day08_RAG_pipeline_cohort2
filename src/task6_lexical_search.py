"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25

BM25 hoạt động thế nào:
    - Term Frequency (TF): từ xuất hiện nhiều trong document → điểm cao
    - Inverse Document Frequency (IDF): từ hiếm → quan trọng hơn
    - Document length normalization: document dài không bị ưu tiên quá mức
"""

import sys
import json
from pathlib import Path
import numpy as np
# pyrefly: ignore [missing-import]
from rank_bm25 import BM25Okapi

# Thêm thư mục gốc dự án vào sys.path để chạy file trực tiếp không bị lỗi import
sys.path.append(str(Path(__file__).parent.parent))

# Đường dẫn đến file vector_store.json chứa corpus đã chia nhỏ từ Task 4
VECTOR_STORE_PATH = Path(__file__).parent.parent / "data" / "vector_store.json"

# CORPUS: Khởi tạo danh sách rỗng, sẽ được load động (lazy load) khi gọi hàm tìm kiếm
CORPUS: list[dict] = []  # List of {'content': str, 'metadata': dict}

# BM25_INDEX: Khởi tạo index rỗng, sẽ được xây dựng một lần duy nhất khi chạy truy vấn đầu tiên
BM25_INDEX = None


def normalize_vietnamese_vowels(text: str) -> str:
    """
    Chuẩn hóa các nguyên âm đôi tiếng Việt dễ bị lệch dấu (ví dụ: hoà -> hòa, tuý -> túy).
    """
    replace_map = {
        "uý": "úy", "uỳ": "ùy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
        "oá": "óa", "oà": "òa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
        "uế": "uế", "uề": "uề", "uể": "uể", "uể": "uể", "uệ": "uệ",
        "oé": "óe", "oè": "òe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    }
    for old, new in replace_map.items():
        text = text.replace(old, new)
    return text


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """
    Xây dựng BM25 index từ corpus.
    
    Args:
        corpus: List of {'content': str, 'metadata': dict}
    """
    # Tokenize: Chuẩn hóa nguyên âm đôi tiếng Việt, chuyển về chữ thường và cắt theo khoảng trắng
    tokenized_corpus = [normalize_vietnamese_vowels(doc["content"]).lower().split() for doc in corpus]
    
    # Khởi tạo mô hình BM25Okapi với corpus đã tách từ
    return BM25Okapi(tokenized_corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng thuật toán BM25.

    Args:
        query: Câu truy vấn từ khóa của người dùng
        top_k: Số lượng kết quả tối đa muốn trả về

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score
            'metadata': dict
        }
        Được sắp xếp giảm dần theo điểm score.
    """
    global CORPUS, BM25_INDEX

    # Bước 1: Nạp corpus từ vector_store.json nếu danh sách rỗng
    if not CORPUS:
        if VECTOR_STORE_PATH.exists():
            with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
                CORPUS = json.load(f)
        else:
            print(f"[!] Khong tim thay file du lieu chunks tai: {VECTOR_STORE_PATH}")
            return []

    if not CORPUS:
        return []

    # Bước 2: Xây dựng index BM25 Okapi nếu chưa khởi tạo
    if BM25_INDEX is None:
        print("[i] Dang xay dung BM25 Index cho du lieu chunks...")
        BM25_INDEX = build_bm25_index(CORPUS)

    # Bước 3: Tokenize câu truy vấn của người dùng (chuẩn hóa nguyên âm đôi)
    tokenized_query = normalize_vietnamese_vowels(query).lower().split()

    # Bước 4: Tính điểm BM25 cho tất cả các chunks trong corpus
    scores = BM25_INDEX.get_scores(tokenized_query)

    # Bước 5: Lấy top_k chỉ mục (indices) của những chunk có điểm cao nhất
    # np.argsort sắp xếp tăng dần -> [::-1] đảo ngược để giảm dần -> [:top_k] cắt lấy top_k
    top_indices = np.argsort(scores)[::-1][:top_k]

    # Bước 6: Lọc kết quả và trả về các kết quả có điểm score > 0 (chứa từ khóa khớp)
    results = []
    for idx in top_indices:
        # scores[idx] > 0 đảm bảo chỉ lấy kết quả thực sự khớp với từ khóa tìm kiếm
        if scores[idx] > 0:
            results.append({
                "content": CORPUS[idx]["content"],
                "score": float(scores[idx]),
                "metadata": CORPUS[idx]["metadata"]
            })
            
    return results


if __name__ == "__main__":
    # Thiết lập stdout sử dụng encoding utf-8 để in tiếng Việt trên console Windows không bị lỗi
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Chạy thử kiểm tra trực tiếp
    print("=" * 50)
    print("Test: Lexical Search (BM25)")
    print("=" * 50)
    
    query_text = "quy định về xác định tình trạng nghiện ma tuý"

    results = lexical_search(query_text, top_k=5)
    
    print(f"\nQuery: '{query_text}'")
    print("-" * 50)
    for i, r in enumerate(results):
        print(f"{i+1}. [{r['score']:.3f}] (Nguon: {r['metadata']['source']})")
        print(f"   Noi dung: {r['content'][:150]}...\n")

