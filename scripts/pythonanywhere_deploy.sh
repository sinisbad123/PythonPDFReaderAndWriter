#!/bin/bash
echo "🐍 Setting up PythonAnywhere deployment package..."
echo "=================================================="
echo

# Navigate to project root from scripts directory
cd "$(dirname "$0")/.."

# Create deployment directory in the organized location
DEPLOY_DIR="deployment/pythonanywhere/pythonanywhere_package"
if [ -d "$DEPLOY_DIR" ]; then
    echo "🗑️  Removing existing deployment package..."
    rm -rf "$DEPLOY_DIR"
fi

echo "📁 Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"

# Create WSGI file for PythonAnywhere
echo "🔧 Creating WSGI configuration..."
cat > "$DEPLOY_DIR/wsgi.py" << 'WSGIEOF'
#!/usr/bin/python3

"""
WSGI config for PDF SKU Processor on PythonAnywhere

This file contains the WSGI configuration required to serve
the Flask application on PythonAnywhere's hosting platform.

Instructions for PythonAnywhere setup:
1. Upload this entire package to /home/yourusername/mysite/
2. Install requirements: pip3.11 install --user -r requirements.txt
3. Set this wsgi.py file in your PythonAnywhere Web tab
4. Set working directory to /home/yourusername/mysite/
5. Reload your web app
"""

import sys
import os

# Add your project directory to sys.path
# IMPORTANT: Replace 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/mysite'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import your Flask application
from flask_app import app as application

# Configure upload directories for PythonAnywhere
upload_dir = os.path.join(project_home, 'uploads')
output_dir = os.path.join(project_home, 'outputs')

# Create directories if they don't exist
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

if __name__ == "__main__":
    application.run(debug=False)
WSGIEOF

# Copy core application files
echo "📋 Copying application files..."
cp src/main.py "$DEPLOY_DIR/"
cp src/flask_app.py "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"

# Copy templates directory
echo "🌐 Copying web templates..."
cp -r src/templates "$DEPLOY_DIR/"

# Create PythonAnywhere-specific requirements.txt
echo "📦 Creating PythonAnywhere requirements..."
cat > "$DEPLOY_DIR/requirements.txt" << 'REQEOF'
PyMuPDF==1.24.11
Flask==3.0.0
Werkzeug==3.0.1
REQEOF

# Create deployment instructions
echo "📖 Creating deployment instructions..."
cat > "$DEPLOY_DIR/PYTHONANYWHERE_SETUP.md" << 'SETUPEOF'
# 🐍 PythonAnywhere Deployment Guide

## 📋 Quick Setup Steps

### 1. 🌐 Create PythonAnywhere Account
- Go to [pythonanywhere.com](https://www.pythonanywhere.com)
- Sign up for a **free account** (no credit card required)
- Choose a username (this will be part of your app URL)

### 2. 📁 Upload Files
1. **Login** to your PythonAnywhere dashboard
2. Go to **"Files"** tab
3. Navigate to `/home/yourusername/mysite/`
4. **Upload all files** from this package to that directory
   - OR use the **"Upload a file"** button to upload the zip

### 3. 📦 Install Dependencies
1. Go to **"Consoles"** tab
2. Start a **"Bash"** console
3. Run these commands:
   ```bash
   cd ~/mysite
   pip3.11 install --user -r requirements.txt
   ```

### 4. 🔧 Configure Web App
1. Go to **"Web"** tab in dashboard
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.11**
5. **IMPORTANT**: Edit the WSGI file settings:
   - **Source code**: `/home/yourusername/mysite/`
   - **WSGI file**: `/home/yourusername/mysite/wsgi.py`
   - **Working directory**: `/home/yourusername/mysite/`

### 5. 🚀 Launch Your App
1. Click **"Reload"** button in Web tab
2. Your app will be available at: `https://yourusername.pythonanywhere.com`
3. **Test it** by uploading a PDF waybill!

## ⚙️ Important Configuration Notes

### 📝 Update WSGI File
**CRITICAL**: Edit `wsgi.py` and replace `yourusername` with your actual PythonAnywhere username:
```python
project_home = '/home/YOURUSERNAME/mysite'  # ← Change this!
```

### 📂 File Permissions
Make sure these directories exist and are writable:
- `/home/yourusername/mysite/uploads/`
- `/home/yourusername/mysite/outputs/`

### 🔄 Updating Your App
To update your app later:
1. Upload new files to `/home/yourusername/mysite/`
2. Click **"Reload"** in the Web tab
3. Changes take effect immediately

## 🌐 Accessing Your App

### 📱 Your Live URL
- **Public URL**: `https://yourusername.pythonanywhere.com`
- **Mobile friendly**: Works on phones, tablets
- **Cross-platform**: Windows 8, macOS, Linux, iOS, Android

### 👥 Sharing with Users
Simply share your PythonAnywhere URL! Users can:
- ✅ Access from any device with a web browser
- ✅ Upload and process PDFs instantly
- ✅ Download results automatically
- ❌ **No Python installation required** on their machines

## 🔧 Troubleshooting

### 🚨 Common Issues

#### "Import Error" or "Module Not Found"
```bash
# Reinstall dependencies
cd ~/mysite
pip3.11 install --user -r requirements.txt --force-reinstall
```

#### "Permission Denied" Errors
```bash
# Fix file permissions
chmod 755 ~/mysite/*.py
chmod -R 755 ~/mysite/templates/
```

#### "WSGI Error"
1. Check that `wsgi.py` has correct username path
2. Verify working directory is set to `/home/yourusername/mysite/`
3. Click "Reload" in Web tab

### 📊 Free Tier Limits
- **Daily CPU**: 100 seconds (resets every 24 hours)
- **Storage**: 512MB total
- **Bandwidth**: 100MB/month outbound
- **Files**: Perfect for PDF processing workload

### 🎯 Usage Tips
- **Best for**: Small to medium PDF processing tasks
- **CPU efficient**: Each PDF processes in ~1-2 seconds
- **Storage efficient**: Temporary files are cleaned automatically

## 🏆 Success!

Once deployed, your PDF SKU Processor will be:
- ✅ **Live 24/7** at your PythonAnywhere URL
- ✅ **Accessible worldwide** via any web browser
- ✅ **Professional-grade** hosting with good uptime
- ✅ **Free forever** (within usage limits)

Share your URL with anyone who needs to process PDF waybills!
SETUPEOF

# Create a quick start script for PythonAnywhere console
echo "🛠️  Creating PythonAnywhere console setup script..."
cat > "$DEPLOY_DIR/pythonanywhere_console_setup.sh" << 'CONSOLEEOF'
#!/bin/bash
# Quick setup script to run in PythonAnywhere console

echo "🐍 PDF SKU Processor - PythonAnywhere Setup"
echo "========================================="
echo

# Navigate to the correct directory
cd ~/mysite

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3.11 install --user -r requirements.txt

# Create necessary directories
echo "📁 Creating upload/output directories..."
mkdir -p uploads outputs

# Set permissions
echo "🔧 Setting file permissions..."
chmod 755 *.py
chmod -R 755 templates/

# Test the Flask app
echo "🧪 Testing Flask application..."
python3.11 -c "
try:
    from flask_app import app
    print('✅ Flask app imports successfully')
    print('✅ Ready to configure in Web tab!')
except Exception as e:
    print(f'❌ Error: {e}')
    print('❌ Check requirements installation')
"

echo
echo "🚀 Setup complete!"
echo "📋 Next steps:"
echo "   1. Configure Web app in PythonAnywhere Web tab"
echo "   2. Set WSGI file to: /home/$(whoami)/mysite/wsgi.py"
echo "   3. Set working directory to: /home/$(whoami)/mysite/"
echo "   4. Click 'Reload' to launch your app"
echo
echo "🌐 Your app will be live at: https://$(whoami).pythonanywhere.com"
CONSOLEEOF

# Make scripts executable
chmod +x "$DEPLOY_DIR/pythonanywhere_console_setup.sh"

# Create a ZIP file for easy upload
echo "📦 Creating deployment ZIP file..."
cd "$DEPLOY_DIR"
tar -czf "../../../pdf_processor_pythonanywhere.tar.gz" . > /dev/null 2>&1
cd ../../..

# Display summary
echo
echo "✅ PythonAnywhere deployment package created successfully!"
echo
echo "📦 Package contents:"
ls -la "$DEPLOY_DIR/"
echo
echo "📋 Files created:"
echo "   📁 $DEPLOY_DIR/ - Complete deployment package"
echo "   📄 pdf_processor_pythonanywhere.tar.gz - Upload-ready archive"
echo
echo "🚀 Next steps:"
echo "   1. Upload 'pdf_processor_pythonanywhere.tar.gz' to PythonAnywhere"
echo "   2. Extract to /home/yourusername/mysite/"
echo "   3. Follow instructions in PYTHONANYWHERE_SETUP.md"
echo "   4. Run pythonanywhere_console_setup.sh in PythonAnywhere console"
echo
echo "🌐 Your app will be live at: https://yourusername.pythonanywhere.com"
echo
