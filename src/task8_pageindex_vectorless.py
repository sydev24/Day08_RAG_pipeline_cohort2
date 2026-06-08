"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký tài khoản tại: https://pageindex.ai/
SDK & sample code: https://github.com/VectifyAI/PageIndex

PageIndex cho phép RAG mà không cần vector store — sử dụng
structural understanding của document thay vì embedding.

Cài đặt:
    pip install pageindex

Hướng dẫn:
    1. Đăng ký account tại pageindex.ai
    2. Lấy API key
    3. Upload documents
    4. Query sử dụng PageIndex API
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def upload_documents():
    """
    Upload toàn bộ markdown documents lên PageIndex.
    """
    if not PAGEINDEX_API_KEY:
        print("[!] PAGEINDEX_API_KEY chua duoc cau hinh trong .env. Bo qua upload.")
        return
        
    try:
        import pageindex
    except ImportError:
        print("[!] Thu vien pageindex chua duoc cai dat. Vui long chay: pip install pageindex")
        return

    # Khởi tạo client phù hợp với phiên bản cài đặt
    if hasattr(pageindex, 'PageIndex'):
        pi = pageindex.PageIndex(api_key=PAGEINDEX_API_KEY)
    elif hasattr(pageindex, 'PageIndexClient'):
        pi = pageindex.PageIndexClient(api_key=PAGEINDEX_API_KEY)
    else:
        print("[!] Khong tim thay class PageIndex hoac PageIndexClient trong thu vien.")
        return

    print(f"[i] Dang upload documents tu {STANDARDIZED_DIR} len PageIndex...")
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        if not md_file.is_file():
            continue
        try:
            if hasattr(pi, 'submit_document'):
                response = pi.submit_document(file_path=str(md_file))
                print(f"  [OK] Uploaded (Client): {md_file.name}, doc_id: {response.get('doc_id')}")
            elif hasattr(pi, 'upload'):
                content = md_file.read_text(encoding="utf-8")
                pi.upload(
                    content=content,
                    metadata={"filename": md_file.name, "type": md_file.parent.name}
                )
                print(f"  [OK] Uploaded (Wrapper): {md_file.name}")
        except Exception as e:
            print(f"  [!] Loi khi upload {md_file.name}: {e}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex.
    Dùng làm fallback khi hybrid search không có kết quả tốt.
    """
    if not PAGEINDEX_API_KEY:
        print("[!] PAGEINDEX_API_KEY chua duoc cau hinh trong .env. Bo qua tim kiem.")
        return []
        
    try:
        import pageindex
    except ImportError:
        print("[!] Thu vien pageindex chua duoc cai dat. Vui long chay: pip install pageindex")
        return []

    try:
        if hasattr(pageindex, 'PageIndex'):
            pi = pageindex.PageIndex(api_key=PAGEINDEX_API_KEY)
        elif hasattr(pageindex, 'PageIndexClient'):
            pi = pageindex.PageIndexClient(api_key=PAGEINDEX_API_KEY)
        else:
            return []

        # Gọi phương thức query thích hợp
        if hasattr(pi, 'query'):
            results = pi.query(query=query, top_k=top_k)
            return [
                {
                    "content": r.text,
                    "score": r.score,
                    "metadata": r.metadata,
                    "source": "pageindex"
                }
                for r in results
            ]
        elif hasattr(pi, 'submit_query'):
            # Với PageIndexClient, ta truy vấn thông qua doc_id
            docs = pi.list_documents()
            results = []
            if docs.get("documents"):
                # Duyệt qua các doc đã upload
                for doc in docs["documents"][:3]:
                    doc_id = doc["doc_id"]
                    resp = pi.submit_query(doc_id=doc_id, query=query)
                    retrieval_id = resp.get("retrieval_id")
                    if retrieval_id:
                        ret_data = pi.get_retrieval(retrieval_id)
                        content = ret_data.get("answer", "")
                        if content:
                            results.append({
                                "content": content,
                                "score": 1.0,
                                "metadata": {"doc_id": doc_id, "filename": doc.get("filename")},
                                "source": "pageindex"
                            })
            return results[:top_k]

        return []
    except Exception as e:
        print(f"[!] Loi khi truy van PageIndex: {e}")
        return []

if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("Uploading documents...")
        upload_documents()

        print("\nTest query:")
        results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
        for r in results:
            print(f"[{r['score']:.3f}] {r['content'][:100]}...")
