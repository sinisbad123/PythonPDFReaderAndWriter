# PDF SKU Reader and Writer

A Python tool that extracts SKU codes and quantities from waybill PDFs and generates comprehensive summary reports with stamped annotations.

## Description

This tool processes waybill PDFs (TikTok, Lazada, etc.) to:
- Extract SKU codes and their quantities from PDF pages
- Handle multi-page orders correctly
- Generate stamped PDFs with SKU information overlaid on each page
- Create detailed summary pages including:
  - All SKUs Summary (with 2-column layout for space efficiency)
  - Multi-SKU Order Patterns (showing mixed orders and their frequency)
  - Mix Orders SKU Count (aggregated SKU counts from multi-SKU orders only)

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

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/sinisbad123/PythonPDFReaderAndWriter.git
   cd PythonPDFReaderAndWriter
   ```

2. **Create and activate virtual environment**
   ```bash
   # On Windows
   python -m venv .venv
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

### Command Line
```bash
# Process a specific PDF file
python main.py "path/to/your/waybill.pdf"

# Interactive mode (will prompt for file path)
python main.py
```

### Using the startup script (Unix/Linux/macOS)
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

## Configuration

Key parameters can be adjusted in `main.py`:
- `bottom_margin`, `left_margin`: Position of stamped text
- `font_size`: Size of stamped text
- `QUANTITY_SEARCH_RANGE_X/Y`: Search area for quantity detection
- `sku_aliases`: Custom SKU name mappings

## Troubleshooting

- **No SKUs detected**: Check if PDF contains text-based (not image-based) SKU information
- **Missing quantities**: Verify quantities appear to the right of SKU codes
- **Two-page orders**: Tool automatically detects based on "Payment" text presence

## Dependencies

- **PyMuPDF**: PDF processing and text extraction
- **re**: Regular expressions for pattern matching
- **os, sys**: File system operations

## License

This project is open source and available under the MIT License.
