# PDF SKU Reader and Writer

A Python tool that extracts SKU codes and quantities from waybill PDFs and generates comprehensive summary reports with stamped annotations. Available as both a command-line tool and a modern web interface.

## Description

This tool processes waybill PDFs (TikTok, Lazada, etc.) to:
- Extract SKU codes and their quantities from PDF pages
- Handle multi-page orders correctly
- Generate stamped PDFs with SKU information overlaid on each page
- Create detailed summary pages including:
  - All SKUs Summary (with 2-column layout for space efficiency)
  - Multi-SKU Order Patterns (showing mixed orders and their frequency)
  - Mix Orders SKU Count (aggregated SKU counts from multi-SKU orders only)

## Interfaces

### 🖥️ Command Line Interface
Traditional terminal-based processing for automation and scripting.

### 🌐 Web Interface
Modern Flask-based web application featuring:
- Drag-and-drop file upload
- Real-time processing progress
- Automatic file download
- Responsive design
- Background processing

## Quick Start (Web Interface)

```bash
# 1. Clone and navigate to project
git clone https://github.com/sinisbad123/PythonPDFReaderAndWriter.git
cd PythonPDFReaderAndWriter

# 2. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start web interface
python3 flask_app.py
```

Then open `http://localhost:5000` in your browser and start processing PDFs!

## Features

- **Smart SKU Detection**: Recognizes SKU patterns starting with 'C_' or 'C '
- **Quantity Calculation**: Automatically detects and calculates quantities, including multipliers (x2, x5, etc.)
- **Two-Page Order Handling**: Correctly associates SKUs across multi-page orders
- **SKU Aliases**: Maps common variations (WASH-L → BWL, WASH-M → BWM)
- **Visual Formatting**: Clean bullet-pointed summaries with drawn circles and proper spacing
- **Intelligent Layout**: 2-column layouts for better space utilization
- **Error Handling**: Robust processing with detailed logging

## Prerequisites

- Python 3.7 or higher
- Virtual environment (recommended)
- Modern web browser (for web interface)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/sinisbad123/PythonPDFReaderAndWriter.git
   cd PythonPDFReaderAndWriter
   ```

2. **Create and activate virtual environment**
   ```bash
   # On Windows
   python3 -m venv .venv
   .venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 🌐 Web Interface (Recommended)

1. **Start the web server**
   ```bash
   # Activate virtual environment first
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   
   # Start the Flask web application
   python3 flask_app.py
   ```
   
   You should see output like:
   ```
   🚀 Starting PDF SKU Processor Web Server...
   📂 Upload folder: /tmp/tmpXXXXXX
   🌐 Server will be available at: http://localhost:5000
   🔄 Auto-opening browser in 1.5 seconds...
   ⚠️  Press Ctrl+C to stop the server
   ```

2. **Access the application**
   - The web browser will automatically open to `http://localhost:5000`
   - If not, manually navigate to that URL in your browser
   - You'll see the "Cheeky Concepts - PDF SKU Processor" interface

3. **Process PDFs**
   - Drag and drop your PDF file onto the upload area, or click to select
   - Wait for the file to be selected (you'll see the filename displayed)
   - Click "🚀 Process PDF" button
   - Monitor the real-time progress on the processing page
   - Once complete, the processed PDF will automatically download
   - Use "🔄 Process Another File" to return to the upload page

4. **Stop the server**
   ```bash
   # Press Ctrl+C in the terminal to stop the web server
   ```

### 🖥️ Command Line Interface

#### Direct execution
```bash
# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Process a specific PDF file
python3 main.py "path/to/your/waybill.pdf"

# Interactive mode (will prompt for file path)
python3 main.py
```

#### Using the startup script (Unix/Linux/macOS)
```bash
# Make executable (first time only)
chmod +x start.sh

# Run the script
./start.sh
```

## Input/Output

**Input**: PDF waybill files containing SKU information
**Output**: New PDF file with suffix `_SKUs_Qty_EndPage.pdf` containing:
- Original pages with SKU stamps in bottom-left corners
- Summary pages with comprehensive SKU analysis

## Example Output

The tool generates several types of summary pages:

1. **All SKUs Summary**: Complete list of all SKUs found across the entire document
2. **Mix Orders Patterns**: Shows patterns of multi-SKU orders and how frequently they occur
3. **Mix Orders SKU Count**: Aggregated SKU counts specifically from multi-SKU orders

## Supported SKU Formats

- Standard format: `C_SKU_NAME`, `C SKU_NAME`
- With quantities: `BWL x3`, `BWM (x2)`
- With numbers: `BWL2` (number becomes multiplier)
- Split SKUs: `BWL/BWM` (processed as separate items)
- Buy-one-take-one: `BWL B1T1` (quantity doubled, B1T1 removed)

## Web Interface Features

- **📁 File Upload**: Drag-and-drop or click to select PDF files (max 100MB)
- **⏳ Real-time Progress**: Live progress tracking with status updates
- **🎨 Modern UI**: Responsive design that works on desktop and mobile
- **🔄 Background Processing**: Non-blocking file processing
- **📥 Auto Download**: Automatic download of processed files
- **✅ Error Handling**: Clear error messages and recovery options
- **🖥️ Cross-platform**: Works on Windows, macOS, and Linux

## Configuration

Key parameters can be adjusted in `main.py`:
- `bottom_margin`, `left_margin`: Position of stamped text
- `font_size`: Size of stamped text
- `QUANTITY_SEARCH_RANGE_X/Y`: Search area for quantity detection
- `sku_aliases`: Custom SKU name mappings

## Troubleshooting

### Command Line Interface
- **No SKUs detected**: Check if PDF contains text-based (not image-based) SKU information
- **Missing quantities**: Verify quantities appear to the right of SKU codes
- **Two-page orders**: Tool automatically detects based on "Weight:" text presence

### Web Interface
- **Server won't start**: Ensure Flask is installed (`pip install Flask`)
- **Browser doesn't open**: Manually navigate to `http://localhost:5000`
- **Upload fails**: Check file is a valid PDF and under 100MB
- **Processing stuck**: Refresh the page and try again with a smaller file
- **Port already in use**: Change the port in `flask_app.py` or kill the existing process

## Dependencies

- **PyMuPDF**: PDF processing and text extraction
- **Flask**: Web framework for the web interface
- **Werkzeug**: WSGI toolkit for Flask
- **re**: Regular expressions for pattern matching
- **os, sys**: File system operations

## License

This project is open source and available under the MIT License.
