# PDF SKU Processor

A professional PDF processing tool that extracts SKU information from TikTok waybills and generates stamped output files. Features both command-line interface and modern web interface for easy deployment.

## 🚀 Features

- **SKU Extraction**: Automatically detects and extracts SKU patterns from PDF waybills
- **Quantity Detection**: Identifies order quantities using "Weight:" field detection
- **Multi-page Support**: Handles both single-page and two-page order formats
- **PDF Stamping**: Adds extracted SKU information as stamps on processed files
- **Web Interface**: Modern drag-and-drop web UI with real-time progress tracking
- **Cross-platform**: Works on Windows, macOS, and Linux
- **PythonAnywhere Ready**: Easy deployment to web hosting platforms

## 📁 Project Structure

```
├── src/                    # Source code
│   ├── main.py            # Core PDF processing logic
│   ├── flask_app.py       # Web interface application
│   └── templates/         # Web UI templates
├── deployment/            # Deployment packages
│   └── pythonanywhere/    # PythonAnywhere deployment files
├── scripts/               # Utility scripts
│   ├── start.sh          # Local development server
│   └── pythonanywhere_deploy.sh  # Deployment package generator
├── docs/                  # Documentation
├── sample_files/          # Sample PDF files for testing
└── requirements.txt       # Python dependencies
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Local Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/sinisbad123/PythonPDFReaderAndWriter.git
   cd PythonPDFReaderAndWriter
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage

### Command Line Interface
Process PDFs directly from the command line:

```bash
python src/main.py input_file.pdf
```

Output files will be generated with `_stamped` suffix.

### Web Interface
Launch the web interface for easy drag-and-drop processing:

```bash
# Using the convenience script
./scripts/start.sh

# Or directly
python src/flask_app.py
```

Then open your browser to `http://localhost:5000`

## 🌐 Web Deployment

### PythonAnywhere Deployment
1. Generate deployment package:
   ```bash
   ./scripts/pythonanywhere_deploy.sh
   ```

2. Upload the generated `pdf_processor_pythonanywhere.tar.gz` to PythonAnywhere

3. Follow the instructions in `PYTHONANYWHERE_SETUP.md`

## 🔧 Configuration

The tool automatically detects:
- **SKU Patterns**: Alphanumeric codes in specific formats
- **Quantity Indicators**: "Weight:" field for two-page orders
- **Order Types**: Single-page vs multi-page waybills

## 📝 Example Processing

### Input
- TikTok waybill PDF with SKU information
- Orders may be single-page or multi-page format

### Output
- Original PDF with extracted SKU stamped
- Filename format: `original_name_stamped.pdf`

### Sample SKU Detection
The tool recognizes patterns like:
- `ABC123DEF456`
- `SKU-789-XYZ`
- Various alphanumeric combinations

## 🐛 Troubleshooting

### Common Issues
1. **Missing Dependencies**: Ensure all packages in `requirements.txt` are installed
2. **PDF Processing Errors**: Check that input files are valid PDF format
3. **Web Interface**: Verify port 5000 is available for local development

### Debug Mode
Enable verbose logging by modifying the Flask app configuration in `src/flask_app.py`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 📞 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Contact the development team

## 🔄 Version History

- **v1.0.0**: Initial release with command-line interface
- **v2.0.0**: Added web interface and PythonAnywhere deployment support
- **v2.1.0**: Improved SKU detection and multi-page order handling

---

Built with ❤️ for efficient PDF processing and SKU management.