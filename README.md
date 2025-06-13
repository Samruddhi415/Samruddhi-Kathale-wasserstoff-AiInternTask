AI Internship Task – Wasserstoff Innovation and Learning Labs
By Samruddhi Kathale

This repository contains my submission for the AI Internship Task assigned by Wasserstoff Innovation and Learning Labs. The project involves building an AI-based solution with a functional backend, model integration, and an explanation of my approach.

Project Overview
The goal of the task was to design and implement an AI-powered application capable of performing [brief 1-liner about what your model does – e.g., "text classification", "OCR + NLP pipeline", etc.].

Key features:

Integration of pre-trained deep learning models

Backend setup with necessary endpoints

Tesseract OCR for image-to-text conversion

Custom preprocessing and post-processing logic

Tech Stack
Python

FastAPI / Flask (choose the one you used)

Tesseract OCR

Hugging Face Transformers

Pydantic

Docker (optional)

Render / Vercel (deployment attempts)

Deployment Notes
While the project is fully functional locally, I faced a few deployment challenges:

Render: The free tier provides only 512 MB memory, which was insufficient to load all models and the Tesseract OCR engine.

Hugging Face API: Custom model deployment requires a paid plan, which was outside the current scope.

Vercel: Not ideal for backend-heavy apps with model loading; better suited for static/frontend apps.

Despite these constraints, the entire working logic is available in this repository and can be run locally.

How to Run Locally
Clone the repo:
bash

git clone https://github.com/SamruddhiKathale/wasserstoff/AiInternTask
cd AiInternTask

Create a virtual environment and install dependencies:

bash
python -m venv venv
source venv/bin/activate  # for Linux/macOS
venv\Scripts\activate     # for Windows

pip install -r requirements.txt

Set up Tesseract:

Install Tesseract OCR

Update the path in .env file:

TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe (for Windows)

Get the Gemini API key
Add to .env file as GEMINI_API_KEY

Run the app:

cd backend
python -m app.main
