#!/bin/bash

echo "🚀 Starting PDF SKU Processor..."
echo "================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Start the Flask web application
echo "🌐 Starting web server..."
echo "📍 Access at: http://localhost:5000"
echo "⚠️  Press Ctrl+C to stop"
echo

python3 src/flask_app.py