#!/bin/bash
# Install Playwright browsers and their system dependencies
pip install playwright
playwright install chromium
python -m spacy download en_core_web_sm
