"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.
"""

from typing import Optional


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.
    """
    if not candidates:
        return []

    # Khởi tạo mô hình CrossEncoder siêu nhẹ (~70MB)
    from sentence_transformers import CrossEncoder
    try:
        model = CrossEncoder("mixedbread-ai/mxbai-rerank-xsmall-v1")
    except Exception:
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        model = CrossEncoder("mixedbread-ai/mxbai-rerank-xsmall-v1")

    # Tạo các cặp đầu vào: (câu hỏi, nội dung tài liệu)
    pairs = [(query, c["content"]) for c in candidates]

    # Dự đoán điểm số liên quan
    scores = model.predict(pairs)

    # Cập nhật lại score mới và sắp xếp giảm dần
    reranked_candidates = []
    for score, candidate in zip(scores, candidates):
        c_copy = candidate.copy()
        c_copy["score"] = float(score)
        reranked_candidates.append(c_copy)

    reranked_candidates.sort(key=lambda x: x["score"], reverse=True)
    return reranked_candidates[:top_k]


def cosine_sim(v1: list[float], v2: list[float]) -> float:
    import numpy as np
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return float(dot_product / (norm_vec1 * norm_vec2))


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.
    """
    if not candidates:
        return []

    selected = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = None
        best_score = float('-inf')

        for idx in remaining:
            # Đảm bảo có vector embedding để tính toán
            if "embedding" not in candidates[idx] or not candidates[idx]["embedding"]:
                continue
                
            # Độ tương đồng với câu hỏi
            relevance = cosine_sim(query_embedding, candidates[idx]["embedding"])

            # Tìm độ tương đồng lớn nhất với những chunk đã được chọn trước đó
            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sim = cosine_sim(candidates[idx]["embedding"], candidates[sel_idx]["embedding"])
                max_sim_to_selected = max(max_sim_to_selected, sim)

            # Công thức MMR
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is None:
            # Fallback nếu không tính được embedding
            best_idx = remaining[0]

        selected.append(best_idx)
        remaining.remove(best_idx)

    return [candidates[i] for i in selected]


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.
    """
    rrf_scores = {}  # content -> score
    content_map = {}  # content -> full dict

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank)
            content_map[key] = item

    # Sắp xếp theo điểm số RRF giảm dần
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content, score in sorted_items[:top_k]:
        item = content_map[content].copy()
        item["score"] = score
        results.append(item)

    return results



# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",  # "cross_encoder" | "mmr" | "rrf"
) -> list[dict]:
    """
    Unified reranking interface.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        # Lấy model embedding từ Task 4 để sinh query_embedding phục vụ MMR
        from sentence_transformers import SentenceTransformer
        from src.task4_chunking_indexing import EMBEDDING_MODEL
        try:
            model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception:
            import os
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            model = SentenceTransformer(EMBEDDING_MODEL)
        query_embedding = model.encode(query).tolist()
        return rerank_mmr(query_embedding, candidates, top_k)
    elif method == "rrf":
        # Nếu gọi RRF đơn lẻ, coi các candidates là 1 danh sách xếp hạng duy nhất
        return rerank_rrf([candidates], top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    # Test with dummy data
    dummy_candidates = [
        {"content": "Điều 248: Tội tàng trữ trái phép chất ma tuý", "score": 0.8, "metadata": {}},
        {"content": "Nghệ sĩ X bị bắt vì sử dụng ma tuý", "score": 0.7, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm cho tội tàng trữ", "score": 0.6, "metadata": {}},
    ]
    results = rerank("hình phạt tàng trữ ma tuý", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
