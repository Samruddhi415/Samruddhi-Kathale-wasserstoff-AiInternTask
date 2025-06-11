from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import shutil
import os
import uuid
import logging
from pathlib import Path

from app.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Document Research & Theme Identification Chatbot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATIC_DIR = os.path.join(BASE_DIR, "static")

print("BASE_DIR =", BASE_DIR)
print("STATIC_DIR =", STATIC_DIR)

if not os.path.exists(STATIC_DIR):
    raise RuntimeError(f"Static directory not found at: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize services
document_processor = DocumentProcessor()
vector_service = VectorService(settings.CHROMA_DB_PATH, settings.EMBEDDING_MODEL)
llm_service = LLMService(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)

# Store document metadata
document_metadata = {}

# Serve index.html from /static
@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/health")
async def health_check():
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say hello")
        gemini_status = bool(response.text.strip())
    except Exception as e:
        logger.error(f"Gemini health check failed: {e}")
        gemini_status = False

    return {
        "status": "healthy",
        "documents_count": vector_service.get_document_count(),
        "gemini_configured": gemini_status
    }


@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload multiple documents"""
    uploaded_files = []
    failed_files = []
    
    for file in files:
        try:
            # Generate unique document ID
            doc_id = f"DOC_{uuid.uuid4().hex[:8]}"
            
            # Save file
            file_extension = Path(file.filename).suffix
            file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_extension}")
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Process document
            processed_doc = document_processor.process_document(file_path, doc_id)
            
            if "error" in processed_doc:
                failed_files.append({
                    "filename": file.filename,
                    "error": processed_doc["error"]
                })
                continue
            
            # Add to vector database
            success = vector_service.add_document(processed_doc)
            
            if success:
                # Store metadata
                document_metadata[doc_id] = {
                    "original_filename": file.filename,
                    "file_path": file_path,
                    "total_pages": processed_doc.get("total_pages", 1),
                    "content_count": len(processed_doc.get("content", []))
                }
                
                uploaded_files.append({
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "pages": processed_doc.get("total_pages", 1),
                    "chunks": len(processed_doc.get("content", []))
                })
            else:
                failed_files.append({
                    "filename": file.filename,
                    "error": "Failed to add to vector database"
                })
        
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "uploaded": uploaded_files,
        "failed": failed_files,
        "total_documents": vector_service.get_document_count()
    }

@app.post("/query")
async def query_documents(query: str = Form(...)):
    """Query documents and get answers with theme identification"""
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Search for relevant documents
        search_results = vector_service.search(query, n_results=50)
        
        if not search_results:
            return {
                "query": query,
                "individual_answers": [],
                "themes": [],
                "synthesis": "No relevant documents found for your query."
            }
        
        # Group results by document
        doc_groups = {}
        for result in search_results:
            doc_id = result["doc_id"]
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(result)
        
        # Get answers from each document
        individual_answers = []
        for doc_id, chunks in doc_groups.items():
            answer_result = llm_service.extract_answer_from_document(query, chunks)
            
            if answer_result["has_answer"]:
                individual_answers.append({
                    "doc_id": doc_id,
                    "filename": document_metadata.get(doc_id, {}).get("original_filename", "Unknown"),
                    "answer": answer_result["answer"],
                    "citation": answer_result.get("citation", ""),
                    "has_answer": True
                })
        
        # Identify themes across all answers
        theme_analysis = llm_service.identify_themes(query, individual_answers)
        
        return {
            "query": query,
            "individual_answers": individual_answers,
            "themes": theme_analysis.get("themes", []),
            "synthesis": theme_analysis.get("overall_synthesis", "")
        }
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    doc_ids = vector_service.get_all_doc_ids()
    documents = []
    
    for doc_id in doc_ids:
        metadata = document_metadata.get(doc_id, {})
        documents.append({
            "doc_id": doc_id,
            "filename": metadata.get("original_filename", "Unknown"),
            "pages": metadata.get("total_pages", 1),
            "chunks": metadata.get("content_count", 0)
        })
    
    return {
        "documents": documents,
        "total_count": len(documents)
    }

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a specific document"""
    try:
        success = vector_service.delete_document(doc_id)
        
        if success and doc_id in document_metadata:
            # Delete file
            file_path = document_metadata[doc_id].get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove metadata
            del document_metadata[doc_id]
        
        return {"success": success, "message": f"Document {doc_id} deleted"}
    
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents")
async def clear_all_documents():
    """Clear all documents"""
    try:
        # Reset vector database
        vector_service.reset_database()
        
        # Delete all uploaded files
        for doc_id, metadata in document_metadata.items():
            file_path = metadata.get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        
        # Clear metadata
        document_metadata.clear()
        
        return {"success": True, "message": "All documents cleared"}
    
    except Exception as e:
        logger.error(f"Error clearing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)