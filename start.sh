#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate academic-rag
streamlit run ui/app.py --server.port 8501