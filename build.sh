#!/usr/bin/env bash
# Build script for Render.com deployment
set -o errexit

pip install --upgrade pip

# Install lightweight CPU PyTorch first for rapid cloud builds
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt

# Install spaCy English model
python -m spacy download en_core_web_sm

# Create required directories
mkdir -p uploads data
