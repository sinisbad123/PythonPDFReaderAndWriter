# 📋 Project Structure Documentation

This document describes the organized structure of the PDF SKU Processor project.

## 📁 Directory Structure

```
PDF_SKU_Processor/
├── 📂 src/                          # Source code
│   ├── main.py                      # Core PDF processing logic
│   ├── flask_app.py                 # Web interface application
│   └── templates/                   # Web UI templates
│       ├── index.html               # Main upload page
│       └── processing.html          # Processing status page
├── 📂 deployment/                   # Deployment packages
│   └── pythonanywhere/              # PythonAnywhere deployment
│       └── pythonanywhere_package/  # Generated deployment package
├── 📂 scripts/                      # Utility scripts
│   ├── start.sh                     # Local development server
│   └── pythonanywhere_deploy.sh     # PythonAnywhere package generator
├── 📂 docs/                         # Documentation
│   └── PYTHONANYWHERE_FIX_GUIDE.md  # I/O blocking fix guide
├── 📂 sample_files/                 # Sample PDF files for testing
├── 📄 requirements.txt              # Python dependencies
├── 📄 README.md                     # Main project documentation
└── 📄 .gitignore                    # Git ignore rules
```

## 📝 File Descriptions

### 🖥️ Source Code (`src/`)
- **`main.py`** - Core PDF processing engine
  - SKU extraction using regex patterns
  - Multi-page order detection
  - PDF stamping functionality
  
- **`flask_app.py`** - Web interface
  - File upload handling with I/O blocking fixes
  - Background processing with progress tracking
  - RESTful API endpoints for status updates
  
- **`templates/`** - Jinja2 templates for web UI
  - Responsive design with drag-and-drop upload
  - Real-time progress indicators
  - Mobile-friendly interface

### 🚀 Deployment (`deployment/`)
- **`pythonanywhere/`** - PythonAnywhere hosting setup
  - Complete deployment package with WSGI configuration
  - Platform-specific setup instructions
  - Automated dependency installation scripts

### 🔧 Scripts (`scripts/`)
- **`start.sh`** - Local development server launcher
- **`pythonanywhere_deploy.sh`** - Automated deployment package generator

### 📚 Documentation (`docs/`)
- **`PYTHONANYWHERE_FIX_GUIDE.md`** - Fixes for I/O blocking issues on shared hosting

### 🧪 Testing (`sample_files/`)
- Sample PDF files for testing the application
- Includes both single-page and multi-page waybills

## 🔄 Development Workflow

### Local Development
```bash
# Start local server
./scripts/start.sh

# Access at http://localhost:5000
```

### PythonAnywhere Deployment
```bash
# Generate deployment package
./scripts/pythonanywhere_deploy.sh

# Upload generated package to PythonAnywhere
# Follow instructions in deployment/pythonanywhere/
```

## 🎯 Key Features Maintained

- ✅ **Organized codebase** with clear separation of concerns
- ✅ **Deployment automation** through scripts
- ✅ **Comprehensive documentation** for setup and troubleshooting
- ✅ **Sample files** for testing functionality
- ✅ **Clean Git repository** with proper ignore rules

This structure supports both local development and cloud deployment while maintaining code organization and documentation standards.
