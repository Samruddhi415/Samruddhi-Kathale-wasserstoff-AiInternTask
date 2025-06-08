import streamlit as st
import requests
import pandas as pd
import json
from typing import List, Dict
import time

# Configure Streamlit page
st.set_page_config(
    page_title="Document Research & Theme Identification Chatbot",
    page_icon="📚",
    layout="wide"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        return response.status_code == 200, response.json()
    except Exception as e:
        st.error(f"API request failed: {e}")
        return False, None

def upload_documents(files):
    """Upload documents to the API"""
    files_data = []
    for file in files:
        files_data.append(("files", (file.name, file.read(), file.type)))
    
    try:
        response = requests.post(f"{API_BASE_URL}/upload", files=files_data)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def query_documents(query: str):
    """Query documents via API"""
    try:
        response = requests.post(f"{API_BASE_URL}/query", data={"query": query})
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_documents():
    """Get list of all documents"""
    try:
        response = requests.get(f"{API_BASE_URL}/documents")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def delete_document(doc_id: str):
    """Delete a specific document"""
    try:
        response = requests.delete(f"{API_BASE_URL}/documents/{doc_id}")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def clear_all_documents():
    """Clear all documents"""
    try:
        response = requests.delete(f"{API_BASE_URL}/documents")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    import time
    time.sleep(2) 
    st.title("📚 Document Research & Theme Identification Chatbot")
    st.markdown("---")
    
    # Check API health
    health_ok, health_info = check_api_health()
    
    if not health_ok:
        st.error("❌ API is not running! Please start the FastAPI backend first.")
        st.code("cd backend && python -m app.main", language="bash")
        return
    
    # Display API status
    with st.sidebar:
        st.success("✅ API is running")
        if health_info:
            st.metric("Documents Loaded", health_info.get("documents_count", 0))
            gemini_status = "✅" if health_info.get("gemini_configured") else "❌"
            st.write(f"Gemini API: {gemini_status}")
    
    # Main interface tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "❓ Query Documents", "📋 Document Management"])
    
    with tab1:
        st.header("Upload Documents")
        st.write("Upload PDF, image, DOCX, or TXT files to build your knowledge base.")
        
        uploaded_files = st.file_uploader(
            "Choose files",
            accept_multiple_files=True,
            type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'docx', 'txt']
        )
        
        if uploaded_files:
            st.write(f"Selected {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size} bytes)")
            
            if st.button("Upload Documents", type="primary"):
                with st.spinner("Processing documents..."):
                    result = upload_documents(uploaded_files)
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success(f"✅ Successfully uploaded {len(result['uploaded'])} documents!")
                    
                    if result['uploaded']:
                        st.subheader("Successfully Uploaded:")
                        upload_df = pd.DataFrame(result['uploaded'])
                        st.dataframe(upload_df, use_container_width=True)
                    
                    if result['failed']:
                        st.subheader("Failed Uploads:")
                        failed_df = pd.DataFrame(result['failed'])
                        st.dataframe(failed_df, use_container_width=True)
                    
                    st.info(f"Total documents in database: {result['total_documents']}")
    
    with tab2:
        st.header("Query Documents")
        st.write("Ask questions about your uploaded documents.")
        
        # Get current document count
        docs_info = get_documents()
        if "error" not in docs_info:
            doc_count = docs_info.get("total_count", 0)
            if doc_count == 0:
                st.warning("⚠️ No documents uploaded yet. Please upload documents first.")
                return
            else:
                st.info(f"📊 {doc_count} documents available for querying")
        
        query = st.text_input(
            "Enter your question:",
            placeholder="e.g., What are the main regulatory requirements mentioned?"
        )
        
        if st.button("Search Documents", type="primary") and query:
            with st.spinner("Searching documents and analyzing themes..."):
                result = query_documents(query)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("✅ Query completed!")
                
                # Display individual document answers
                if result.get("individual_answers"):
                    st.subheader("📄 Individual Document Answers")
                    
                    # Create DataFrame for table display
                    answers_data = []
                    for answer in result["individual_answers"]:
                        answers_data.append({
                            "Document ID": answer["doc_id"],
                            "Filename": answer["filename"],
                            "Answer": answer["answer"][:200] + "..." if len(answer["answer"]) > 200 else answer["answer"],
                            "Citation": answer["citation"]
                        })
                    
                    answers_df = pd.DataFrame(answers_data)
                    st.dataframe(answers_df, use_container_width=True)
                    
                    # Show full answers in expandable sections
                    st.subheader("📖 Full Answers")
                    for answer in result["individual_answers"]:
                        with st.expander(f"{answer['doc_id']} - {answer['filename']}"):
                            st.write(f"**Answer:** {answer['answer']}")
                            st.write(f"**Citation:** {answer['citation']}")
                
                # Display theme analysis
                if result.get("themes"):
                    st.subheader("🎯 Theme Analysis")
                    
                    for i, theme in enumerate(result["themes"], 1):
                        st.markdown(f"**Theme {i}: {theme['theme_name']}**")
                        st.write(theme["description"])
                        st.write(f"**Supporting Documents:** {', '.join(theme['supporting_documents'])}")
                        st.write(f"**Synthesized Answer:** {theme['synthesized_answer']}")
                        st.markdown("---")
                
                # Display overall synthesis
                if result.get("synthesis"):
                    st.subheader("📝 Overall Synthesis")
                    st.write(result["synthesis"])
                
                if not result.get("individual_answers") and not result.get("themes"):
                    st.warning("No relevant information found for your query.")
    
    with tab3:
        st.header("Document Management")
        st.write("View and manage your uploaded documents.")
        
        # Refresh button
        if st.button("🔄 Refresh Document List"):
            st.rerun()
        
        # Get documents
        docs_result = get_documents()
        
        if "error" in docs_result:
            st.error(f"Error loading documents: {docs_result['error']}")
        elif docs_result.get("documents"):
            st.subheader(f"📚 {docs_result['total_count']} Documents")
            
            # Display documents table
            docs_df = pd.DataFrame(docs_result["documents"])
            st.dataframe(docs_df, use_container_width=True)
            
            # Document actions
            st.subheader("🔧 Document Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Delete specific document
                doc_ids = [doc["doc_id"] for doc in docs_result["documents"]]
                selected_doc = st.selectbox("Select document to delete:", [""] + doc_ids)
                
                if selected_doc and st.button("🗑️ Delete Selected Document", type="secondary"):
                    with st.spinner("Deleting document..."):
                        delete_result = delete_document(selected_doc)
                    
                    if "error" in delete_result:
                        st.error(f"Error: {delete_result['error']}")
                    else:
                        st.success(f"✅ Document {selected_doc} deleted!")
                        st.rerun()
            
            with col2:
                st.warning("⚠️ This will delete ALL documents permanently!")
                confirm_clear = st.checkbox("I understand this will delete all documents")
                
                if confirm_clear and st.button("🗑️ Clear All Documents", type="secondary"):
                    with st.spinner("Clearing all documents..."):
                        clear_result = clear_all_documents()
                    
                    if "error" in clear_result:
                        st.error(f"Error: {clear_result['error']}")
                    else:
                        st.success("✅ All documents cleared!")
                        st.rerun()
        else:
            st.info("📭 No documents uploaded yet.")

if __name__ == "__main__":
    main()