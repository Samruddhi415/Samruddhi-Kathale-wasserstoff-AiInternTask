#!/bin/bash

# Start FastAPI backend in background
python -m backend.app.main &

# Start Streamlit frontend on same port (Render will use port 8000)
streamlit run streamlit_app.py --server.port 8000 --server.enableCORS false
