import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, db_path: str, embedding_model: str):
        self.db_path = db_path
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(allow_reset=True)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_document(self, doc_data: Dict) -> bool:
        """Add processed document to vector database"""
        try:
            doc_id = doc_data["doc_id"]
            content_list = doc_data["content"]
            
            if not content_list:
                logger.warning(f"No content to add for document {doc_id}")
                return False
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            
            for item in content_list:
                chunk_id = f"{doc_id}_{item['page']}_{item['paragraph']}"
                ids.append(chunk_id)
                documents.append(item["text"])
                metadatas.append({
                    "doc_id": doc_id,
                    "page": item["page"],
                    "paragraph": item["paragraph"],
                    "citation": item["citation"]
                })
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} chunks for document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {doc_data.get('doc_id')}: {str(e)}")
            return False
    
    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        """Search for relevant documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]
                    
                    formatted_results.append({
                        "doc_id": metadata["doc_id"],
                        "text": doc,
                        "citation": metadata["citation"],
                        "page": metadata["page"],
                        "paragraph": metadata["paragraph"],
                        "relevance_score": 1 - distance  # Convert distance to similarity
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            return []
    
    def get_document_count(self) -> int:
        """Get total number of unique documents"""
        try:
            # Get all unique doc_ids
            results = self.collection.get(include=["metadatas"])
            if results["metadatas"]:
                doc_ids = set(meta["doc_id"] for meta in results["metadatas"])
                return len(doc_ids)
            return 0
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0
    
    def get_all_doc_ids(self) -> List[str]:
        """Get all unique document IDs"""
        try:
            results = self.collection.get(include=["metadatas"])
            if results["metadatas"]:
                doc_ids = list(set(meta["doc_id"] for meta in results["metadatas"]))
                return doc_ids
            return []
        except Exception as e:
            logger.error(f"Error getting doc IDs: {str(e)}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks of a document"""
        try:
            # Get all chunks for this document
            results = self.collection.get(
                where={"doc_id": doc_id},
                include=["metadatas"]
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted document {doc_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False
    
    def reset_database(self) -> bool:
        """Reset the entire database"""
        try:
            # Close existing client
            del self.client
            del self.collection
            
            # Recreate client and collection
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=ChromaSettings(allow_reset=True)
            )
            
            # Reset and recreate collection
            self.client.reset()
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            return False