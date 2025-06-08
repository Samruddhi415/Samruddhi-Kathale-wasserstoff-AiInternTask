import google.generativeai as genai
from typing import List, Dict, Any
import logging
import json
import re

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str, model_name: str = "models/gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
    def extract_answer_from_document(self, query: str, document_chunks: List[Dict]) -> Dict:
        """Extract answer from a single document's chunks"""
        try:
            # Combine all chunks from the document
            doc_text = "\n\n".join([chunk["text"] for chunk in document_chunks])
            doc_id = document_chunks[0]["doc_id"]
            
            prompt = f"""
            Based on the following document content, answer the user's question.
            If the document contains relevant information, provide a clear answer.
            If the document doesn't contain relevant information, respond with "NO_RELEVANT_INFO".
            
            Document ID: {doc_id}
            Document Content:
            {doc_text}
            
            Question: {query}
            
            Provide your answer in the following JSON format:
            {{
                "has_answer": true/false,
                "answer": "your answer here or NO_RELEVANT_INFO",
                "relevant_chunks": [list of chunk indices that support the answer]
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON response
            try:
                result = json.loads(response.text)
            except:
                # Fallback parsing
                if "NO_RELEVANT_INFO" in response.text:
                    result = {
                        "has_answer": False,
                        "answer": "NO_RELEVANT_INFO",
                        "relevant_chunks": []
                    }
                else:
                    result = {
                        "has_answer": True,
                        "answer": response.text,
                        "relevant_chunks": [0]  # Default to first chunk
                    }
            
            # Add citation information
            if result["has_answer"]:
                citations = []
                for chunk_idx in result.get("relevant_chunks", [0]):
                    if chunk_idx < len(document_chunks):
                        citations.append(document_chunks[chunk_idx]["citation"])
                
                result["citation"] = ", ".join(citations) if citations else document_chunks[0]["citation"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting answer from document: {str(e)}")
            return {
                "has_answer": False,
                "answer": f"Error processing document: {str(e)}",
                "relevant_chunks": []
            }
    
    def identify_themes(self, query: str, document_answers: List[Dict]) -> Dict:
        """Identify common themes across all document answers"""
        try:
            # Filter documents that have relevant answers
            relevant_answers = [
                doc for doc in document_answers 
                if doc.get("has_answer", False) and doc.get("answer", "") != "NO_RELEVANT_INFO"
            ]
            
            if not relevant_answers:
                return {
                    "themes": [],
                    "synthesis": "No relevant information found across the documents for this query."
                }
            
            # Prepare context for theme identification
            answers_context = ""
            for i, doc in enumerate(relevant_answers):
                answers_context += f"Document {doc['doc_id']}: {doc['answer']}\n\n"
            
            prompt = f"""
            Analyze the following answers from different documents and identify common themes.
            Group similar information together and provide a synthesized response.
            
            Original Query: {query}
            
            Document Answers:
            {answers_context}
            
            Provide your analysis in the following JSON format:
            {{
                "themes": [
                    {{
                        "theme_name": "Give a concise, meaningful name for this theme",
                        "description": "Description of what this theme covers",
                        "supporting_documents": ["DOC001", "DOC002"],
                        "synthesized_answer": "Combined answer for this theme"
                    }}
                ],
                "overall_synthesis": "Overall summary combining all themes"
            }}
            
            Requirements:
            - Identify 1-3 main themes maximum
            - Each theme should have at least 2 supporting documents (if possible)
            - Provide clear, coherent synthesized answers
            - Reference specific document IDs
            """
            
            response = self.model.generate_content(prompt)
            
            try:
                result = json.loads(response.text)
            except:
                # Fallback parsing
                themes = []
                if relevant_answers:
                    # Create a simple theme grouping
                    theme = {
                        "theme_name": "Main Theme",
                        "description": f"Information related to: {query}",
                        "supporting_documents": [doc["doc_id"] for doc in relevant_answers],
                        "synthesized_answer": self._simple_synthesis(relevant_answers)
                    }
                    themes.append(theme)
                
                result = {
                    "themes": themes,
                    "overall_synthesis": self._simple_synthesis(relevant_answers)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error identifying themes: {str(e)}")
            return {
                "themes": [],
                "synthesis": f"Error analyzing themes: {str(e)}"
            }
    
    def _simple_synthesis(self, document_answers: List[Dict]) -> str:
        """Simple fallback synthesis when JSON parsing fails"""
        try:
            all_answers = " ".join([doc.get("answer", "") for doc in document_answers])
            
            prompt = f"""
            Provide a brief synthesis of the following information:
            {all_answers}
            
            Keep it concise and coherent, highlighting the main points.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"Multiple documents provide information about this topic. Please see individual document answers for details."
    
    def answer_general_question(self, query: str, context: str = "") -> str:
        """Answer general questions with optional context"""
        try:
            prompt = f"""
            Answer the following question clearly and concisely.
            
            {f"Context: {context}" if context else ""}
            
            Question: {query}
            """
            
            response = self.model.generate_content(prompt)
            print("🔍 Raw Gemini response:\n", response.text)

            return response.text
            
        except Exception as e:
            logger.error(f"Error answering general question: {str(e)}")
            return f"Error generating response: {str(e)}"