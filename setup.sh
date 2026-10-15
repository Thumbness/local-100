#!/bin/bash

echo "Setting up the environment..."

if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 to proceed."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "pip is not installed. Please install pip to proceed."
    exit 1
fi

if [ -d "venv" ]; then
    echo "Virtual environment detected."
    source venv/Scripts/activate
else
    echo "No virtual environment detected. Creating one..."
    python -m venv venv
    source venv/Scripts/activate
fi

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
else
    echo "requirements.txt not found. Please ensure it exists in the current directory."
    exit 1
fi

pip install -r requirements.txt
python -m src.application.setup

echo "Setup complete. Run the application using ./run.sh"