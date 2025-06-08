#!/bin/bash

# Start FastAPI backend on 0.0.0.0:8000
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit frontend on 0.0.0.0:8501
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501
