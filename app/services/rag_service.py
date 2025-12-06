import os, io, json
import numpy as np
from ..db import get_db

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except Exception:
    SentenceTransformer = None
    faiss = None

# Document processing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import python_docx2txt
    DOC_AVAILABLE = True
except ImportError:
    DOC_AVAILABLE = False

_model = None
_index = None
_meta = []

def _ensure_model():
    global _model
    if _model is None and SentenceTransformer is not None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def _extract_text_from_file(filename: str, data: bytes) -> str:
    """Extract text from various file formats"""
    file_ext = os.path.splitext(filename.lower())[1]
    
    try:
        if file_ext == '.pdf':
            return _extract_pdf_text(data)
        elif file_ext == '.docx':
            return _extract_docx_text(data)
        elif file_ext == '.doc':
            return _extract_doc_text(data)
        elif file_ext in ['.txt', '.md']:
            return data.decode("utf-8", errors="ignore")
        else:
            # Fallback: try to decode as text
            return data.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        # Fallback to raw decode
        return data.decode("utf-8", errors="ignore")

def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF using PyPDF2"""
    if not PDF_AVAILABLE:
        return "[PDF support not available. Install PyPDF2: pip install PyPDF2]"
    
    try:
        pdf_file = io.BytesIO(data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"[Error reading PDF: {e}]"

def _extract_docx_text(data: bytes) -> str:
    """Extract text from DOCX using python-docx"""
    if not DOCX_AVAILABLE:
        return "[DOCX support not available. Install python-docx: pip install python-docx]"
    
    try:
        docx_file = io.BytesIO(data)
        doc = DocxDocument(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"[Error reading DOCX: {e}]"

def _extract_doc_text(data: bytes) -> str:
    """Extract text from DOC files"""
    if not DOC_AVAILABLE:
        return "[DOC support not available. Install docx2txt: pip install docx2txt]"
    
    try:
        # Save temporarily to extract text (DOC files need file path)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
            temp_file.write(data)
            temp_file.flush()
            text = python_docx2txt.process(temp_file.name)
            os.unlink(temp_file.name)  # Clean up temp file
        return text
    except Exception as e:
        return f"[Error reading DOC: {e}]"

def ingest_document(filename:str, data:bytes, namespace:str="default")->bool:
    db = get_db()
    path = os.path.join("uploads", filename)
    with open(path,"wb") as f:
        f.write(data)
    db.execute("INSERT INTO documents(path,metadata_json,namespace) VALUES(?,?,?)", (path, json.dumps({"filename":filename}), namespace))
    doc_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    
    # Extract text based on file type
    text = _extract_text_from_file(filename, data)
    
    # Smart chunking: split by paragraphs first, then by size
    chunks = _smart_chunk_text(text, max_chunk_size=800)
    
    model = _ensure_model()
    for idx, ch in enumerate(chunks):
        emb = None
        if model and ch.strip():  # Only embed non-empty chunks
            emb = model.encode([ch])[0].astype("float32").tobytes()
        db.execute("INSERT INTO chunks(document_id,chunk_index,text,embedding) VALUES(?,?,?,?)",
                   (doc_id, idx, ch, emb))
    db.commit()
    return True

def _smart_chunk_text(text: str, max_chunk_size: int = 800) -> list:
    """Intelligently chunk text by paragraphs and sentences"""
    if not text.strip():
        return []
    
    # First split by paragraphs
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If paragraph is too long, split by sentences
        if len(paragraph) > max_chunk_size:
            sentences = paragraph.split('. ')
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                if len(current_chunk) + len(sentence) > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = sentence
                    else:
                        # Single sentence is too long, force split
                        chunks.append(sentence[:max_chunk_size])
                        if len(sentence) > max_chunk_size:
                            current_chunk = sentence[max_chunk_size:]
                        else:
                            current_chunk = ""
                else:
                    current_chunk += ". " + sentence if current_chunk else sentence
        else:
            # Paragraph fits, try to add it
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    chunks.append(paragraph)
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def reindex_all():
    # in-ram FAISS build for quick search
    global _index, _meta
    _meta = []
    db = get_db()
    rows = db.execute("SELECT id,text,embedding FROM chunks WHERE embedding IS NOT NULL").fetchall()
    if not rows or faiss is None:
        _index = None
        return {"ok": True, "count": 0}
    vecs = []
    for r in rows:
        emb = np.frombuffer(r["embedding"], dtype="float32")
        vecs.append(emb)
        _meta.append({"chunk_id": r["id"], "text": r["text"]})
    arr = np.vstack(vecs)
    _index = faiss.IndexFlatIP(arr.shape[1])
    faiss.normalize_L2(arr)
    _index.add(arr)
    return {"ok": True, "count": len(_meta)}

def semantic_search(q:str, namespace:str="default"):
    model = _ensure_model()
    if not model or _index is None:
        # fallback to LIKE search
        db = get_db()
        rows = db.execute("SELECT text FROM chunks WHERE text LIKE ? LIMIT 5", (f"%{q}%",)).fetchall()
        return {"results":[{"text": r["text"]} for r in rows], "mode":"fallback"}
    qv = model.encode([q]).astype("float32")
    import faiss
    faiss.normalize_L2(qv)
    D,I = _index.search(qv, 5)
    out = [{"text": _meta[i]["text"], "score": float(D[0][k])} for k,i in enumerate(I[0]) if i!=-1]
    return {"results": out, "mode":"semantic"}

def indexing_status():
    db = get_db()
    count_docs = db.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    count_chunks = db.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
    return {"documents": count_docs, "chunks": count_chunks}
