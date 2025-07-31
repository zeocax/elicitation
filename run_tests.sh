#!/bin/bash

echo "Installing test dependencies..."
pip install -r tests/requirements-test.txt

echo -e "\nRunning LLM tests..."
python -m pytest tests/test_llm.py -v