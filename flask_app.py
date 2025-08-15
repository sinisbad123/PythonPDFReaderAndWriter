#!/usr/bin/env python3

from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
import os
import tempfile
import threading
import webbrowser
import time
import json
from werkzeug.utils import secure_filename
from main import extract_sku_locations_from_pdf, stamp_skus_on_pdf

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'pdf'}

# Global dictionary to track processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_pdf_background(task_id, filepath, filename):
    """Process PDF in background thread with progress tracking"""
    try:
        # Update status: Starting extraction
        processing_status[task_id].update({
            'status': 'extracting',
            'progress': 20,
            'message': 'Extracting SKU locations from PDF...'
        })
        
        # Extract SKUs
        sku_locations = extract_sku_locations_from_pdf(filepath)
        
        if sku_locations is None:
            processing_status[task_id].update({
                'status': 'error',
                'progress': 100,
                'message': 'Failed to extract SKU locations from the PDF.',
                'error': 'Failed to extract SKU locations from the PDF.'
            })
            return
            
        if not sku_locations:
            processing_status[task_id].update({
                'status': 'error',
                'progress': 100,
                'message': 'No SKUs were identified in the PDF using the current patterns.',
                'error': 'No SKUs were identified in the PDF using the current patterns.'
            })
            return
        
        # Update status: Processing SKUs
        processing_status[task_id].update({
            'status': 'processing',
            'progress': 50,
            'message': f'Found {len(sku_locations)} SKUs. Processing multi-SKU orders...'
        })
        
        # Process multi-SKU orders
        multi_sku_orders = {}
        for sku_info in sku_locations:
            order_id = sku_info.get('order_id', 'UNKNOWN_ORDER')
            if order_id not in multi_sku_orders:
                multi_sku_orders[order_id] = []
            multi_sku_orders[order_id].append(sku_info)

        filtered_multi_sku_orders = {}
        for order_id, skus_list in multi_sku_orders.items():
            unique_skus_in_order = set(sku_info['sku'] for sku_info in skus_list)
            if len(unique_skus_in_order) > 1:
                filtered_multi_sku_orders[order_id] = skus_list
        
        # Update status: Creating output
        processing_status[task_id].update({
            'status': 'stamping',
            'progress': 80,
            'message': 'Creating output PDF with SKU stamps...'
        })
        
        # Create output file
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_SKUs_Qty_EndPage.pdf"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        
        # Stamp SKUs
        success = stamp_skus_on_pdf(filepath, sku_locations, output_path, filtered_multi_sku_orders)
        
        if success and os.path.exists(output_path):
            processing_status[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': f'Successfully processed PDF! Found {len(sku_locations)} SKUs.',
                'output_path': output_path,
                'output_filename': output_filename
            })
        else:
            processing_status[task_id].update({
                'status': 'error',
                'progress': 100,
                'message': 'Failed to create output PDF.',
                'error': 'Failed to create output PDF.'
            })
    
    except Exception as e:
        processing_status[task_id].update({
            'status': 'error',
            'progress': 100,
            'message': f'Error processing PDF: {str(e)}',
            'error': str(e)
        })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return redirect(url_for('index'))
    
    print(f"Request method: {request.method}")
    print(f"Files in request: {list(request.files.keys())}")
    
    if 'file' not in request.files:
        print("No 'file' key in request.files")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    print(f"File object: {file}")
    print(f"Filename: '{file.filename}'")
    
    if file.filename == '':
        print("Empty filename")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Generate a unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Initialize processing status
        processing_status[task_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Starting PDF processing...',
            'filename': filename,
            'output_path': None,
            'error': None
        }
        
        # Start processing in background thread
        thread = threading.Thread(target=process_pdf_background, args=(task_id, filepath, filename))
        thread.daemon = True
        thread.start()
        
        # Return processing page
        return render_template('processing.html', task_id=task_id, filename=filename)
    else:
        flash('Please select a valid PDF file', 'error')
        return redirect(url_for('index'))

@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Get processing progress for a task"""
    if task_id in processing_status:
        return jsonify(processing_status[task_id])
    else:
        return jsonify({'status': 'not_found', 'message': 'Task not found'}), 404

@app.route('/download/<task_id>')
def download_result(task_id):
    """Download the processed PDF file"""
    if task_id in processing_status:
        status = processing_status[task_id]
        if status['status'] == 'completed' and status['output_path'] and os.path.exists(status['output_path']):
            return send_file(status['output_path'], 
                           as_attachment=True, 
                           download_name=status['output_filename'],
                           mimetype='application/pdf')
        else:
            flash('File not ready or not found', 'error')
            return redirect(url_for('index'))
    else:
        flash('Task not found', 'error')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "PDF SKU Processor is running"})

def open_browser():
    """Open web browser after a short delay"""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cheeky Concepts - PDF SKU Processor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .info-card {
            background: #f8f9fa;
            border-left: 4px solid #4facfe;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 0 8px 8px 0;
        }
        
        .info-card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
        }
        
        .info-card ul {
            list-style-position: inside;
            color: #555;
        }
        
        .info-card li {
            margin: 8px 0;
            padding-left: 10px;
        }
        
        .upload-section {
            text-align: center;
            margin: 30px 0;
        }
        
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 60px 20px;
            transition: all 0.3s ease;
            background: #fafafa;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .upload-area:hover {
            border-color: #4facfe;
            background: #f0f8ff;
            transform: translateY(-2px);
        }
        
        .upload-area::before {
            content: '📄';
            font-size: 3em;
            display: block;
            margin-bottom: 15px;
        }
        
        .upload-area h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .file-input-wrapper {
            position: relative;
            display: inline-block;
            margin: 15px 0;
        }
        
        .file-input {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        
        .file-input-label {
            display: inline-block;
            padding: 12px 30px;
            background: #4facfe;
            color: white;
            border-radius: 25px;
            cursor: pointer;
            transition: background 0.3s ease;
            font-weight: 500;
        }
        
        .file-input-label:hover {
            background: #3498db;
        }
        
        .process-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1em;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
            font-weight: 500;
        }
        
        .process-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .process-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-weight: 500;
        }
        
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-warning {
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }
        
        .selected-file {
            background: #e3f2fd;
            border: 2px solid #2196f3;
            color: #1565c0;
        }
        
        @media (max-width: 600px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .content {
                padding: 20px;
            }
            
            .upload-area {
                padding: 40px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cheeky Concepts - PDF SKU Processor</h1>
            <p>Extract and process SKU codes from PDF waybills</p>
        </div>
        
        <div class="content">
            <div class="info-card">
                <h3>✨ What this tool does:</h3>
                <ul>
                    <li>Extracts SKU codes from PDF waybill documents</li>
                    <li>Handles "+" and "/" separators in SKU codes (e.g., "C_9oz2+6m" → "9oz (x4)" + "6m (x2)")</li>
                    <li>Calculates proper quantities for each SKU part</li>
                    <li>Creates a new PDF with SKUs stamped on each page</li>
                    <li>Generates comprehensive summary pages with SKU counts and patterns</li>
                </ul>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form action="{{ url_for('upload_file') }}" method="post" enctype="multipart/form-data" id="uploadForm">
                <div class="upload-section">
                    <div class="upload-area" id="uploadArea">
                        <h3>Select Your PDF File</h3>
                        <p>Click here or drag and drop your PDF waybill</p>
                        <div class="file-input-wrapper">
                            <input type="file" id="fileInput" name="file" accept=".pdf" required class="file-input" onchange="handleFileSelect(this)">
                            <label for="fileInput" class="file-input-label">Choose File</label>
                        </div>
                        <button type="submit" class="process-btn" id="processBtn" disabled>Process PDF</button>
                    </div>
                </div>
            </form>
            
            <div class="info-card">
                <p><strong>📝 Note:</strong> Maximum file size is 100MB. Processing may take a few moments for large files with many pages.</p>
            </div>
        </div>
        
        <div class="footer">
            Cheeky Concepts - PDF SKU Processor v1.0 - Built with Flask & PyMuPDF
        </div>
    </div>
    
    <script>
        function handleFileSelect(input) {
            const uploadArea = document.getElementById('uploadArea');
            
            if (input.files.length > 0) {
                const file = input.files[0];
                uploadArea.classList.add('selected-file');
                
                // Keep the original file input but hide it
                const originalInput = document.getElementById('fileInput');
                
                uploadArea.innerHTML = `
                    <h3>📄 File Selected</h3>
                    <p><strong>${file.name}</strong></p>
                    <p>Size: ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    <button type="button" onclick="clearFile()" style="background: #dc3545; color: white; border: none; padding: 8px 15px; border-radius: 15px; margin: 10px; cursor: pointer;">Change File</button>
                    <button type="submit" class="process-btn">🚀 Process PDF</button>
                `;
                
                // Re-append the hidden file input to maintain the form data
                originalInput.style.display = 'none';
                uploadArea.appendChild(originalInput);
            }
        }
        
        function clearFile() {
            const uploadArea = document.getElementById('uploadArea');
            
            uploadArea.classList.remove('selected-file');
            uploadArea.innerHTML = `
                <h3>Select Your PDF File</h3>
                <p>Click here or drag and drop your PDF waybill</p>
                <div class="file-input-wrapper">
                    <input type="file" id="fileInput" name="file" accept=".pdf" required class="file-input" onchange="handleFileSelect(this)">
                    <label for="fileInput" class="file-input-label">Choose File</label>
                </div>
                <button type="submit" class="process-btn" id="processBtn" disabled>Process PDF</button>
            `;
        }
        
        // Handle drag and drop
        const uploadArea = document.getElementById('uploadArea');
        let isDraggedFile = false;
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#4facfe';
            uploadArea.style.background = '#f0f8ff';
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#ddd';
            uploadArea.style.background = '#fafafa';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#ddd';
            uploadArea.style.background = '#fafafa';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                isDraggedFile = true;
                const fileInput = document.getElementById('fileInput');
                fileInput.files = files;
                handleFileSelect(fileInput);
                
                // Reset flag after a short delay
                setTimeout(() => {
                    isDraggedFile = false;
                }, 100);
            }
        });
        
        // Modify the upload area click handler to check for drag and drop
        uploadArea.addEventListener('click', (e) => {
            // Don't open file dialog if clicking on buttons or if file was just dragged
            if (isDraggedFile || 
                e.target.tagName === 'BUTTON' || 
                e.target.tagName === 'LABEL' ||
                e.target.closest('button') || 
                e.target.closest('label')) {
                return;
            }
            document.getElementById('fileInput').click();
        });
        
        // Show processing message when form is submitted
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            const processBtn = document.querySelector('.process-btn');
            const fileInput = document.getElementById('fileInput');
            
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                alert('Please select a file first!');
                return;
            }
            
            processBtn.textContent = '⏳ Uploading...';
            processBtn.disabled = true;
        });
    </script>
</body>
</html>"""
    
    with open('templates/index.html', 'w') as f:
        f.write(html_template)
    
    # Create processing template
    processing_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Processing PDF - Cheeky Concepts</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .processing-container {
            max-width: 600px;
            width: 100%;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            text-align: center;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .content {
            padding: 40px;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4facfe;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .progress-container {
            width: 100%;
            background-color: #f0f0f0;
            border-radius: 25px;
            margin: 20px 0;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .progress-bar {
            height: 20px;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            border-radius: 25px;
            transition: width 0.5s ease;
            position: relative;
        }
        
        .progress-bar::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background-image: linear-gradient(
                -45deg,
                rgba(255, 255, 255, 0.2) 25%,
                transparent 25%,
                transparent 50%,
                rgba(255, 255, 255, 0.2) 50%,
                rgba(255, 255, 255, 0.2) 75%,
                transparent 75%,
                transparent
            );
            background-size: 30px 30px;
            animation: progress-animation 1s linear infinite;
        }
        
        @keyframes progress-animation {
            0% { background-position: 0 0; }
            100% { background-position: 30px 0; }
        }
        
        .progress-text {
            font-weight: 600;
            color: #333;
            margin-top: 10px;
        }
        
        .file-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        
        .file-info h3 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .status-message {
            font-size: 1.1em;
            color: #555;
            margin: 20px 0;
            min-height: 1.5em;
        }
        
        .success-container {
            display: none;
        }
        
        .success-container.show {
            display: block;
        }
        
        .download-btn {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 1.1em;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 20px 10px;
        }
        
        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            text-decoration: none;
            color: white;
        }
        
        .back-btn {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 1em;
            border-radius: 20px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }
        
        .back-btn:hover {
            transform: translateY(-1px);
            text-decoration: none;
            color: white;
        }
        
        .error-container {
            display: none;
            color: #dc3545;
        }
        
        .error-container.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="processing-container">
        <div class="header">
            <h1>Processing Your PDF</h1>
            <p>Please wait while we extract and process SKU codes...</p>
        </div>
        
        <div class="content">
            <div class="file-info">
                <h3>📄 Processing File</h3>
                <p><strong>{{ filename }}</strong></p>
            </div>
            
            <div id="processingSection">
                <div class="spinner"></div>
                
                <div class="progress-container">
                    <div class="progress-bar" id="progressBar" style="width: 0%"></div>
                </div>
                
                <div class="progress-text" id="progressText">0%</div>
                
                <div class="status-message" id="statusMessage">Starting processing...</div>
            </div>
            
            <div id="successContainer" class="success-container">
                <h3 style="color: #28a745; margin-bottom: 20px;">✅ Processing Complete!</h3>
                <p id="successMessage"></p>
                <a href="#" id="downloadBtn" class="download-btn">📥 Download Processed PDF</a>
                <br>
                <a href="{{ url_for('index') }}" class="back-btn">🔄 Process Another File</a>
            </div>
            
            <div id="errorContainer" class="error-container">
                <h3 style="color: #dc3545; margin-bottom: 20px;">❌ Processing Failed</h3>
                <p id="errorMessage"></p>
                <a href="{{ url_for('index') }}" class="back-btn">🔄 Try Again</a>
            </div>
        </div>
    </div>
    
    <script>
        const taskId = '{{ task_id }}';
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const statusMessage = document.getElementById('statusMessage');
        const processingSection = document.getElementById('processingSection');
        const successContainer = document.getElementById('successContainer');
        const errorContainer = document.getElementById('errorContainer');
        const downloadBtn = document.getElementById('downloadBtn');
        
        function updateProgress() {
            fetch(`/progress/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    console.log('Progress update:', data);
                    
                    // Update progress bar
                    progressBar.style.width = data.progress + '%';
                    progressText.textContent = data.progress + '%';
                    statusMessage.textContent = data.message;
                    
                    if (data.status === 'completed') {
                        // Hide processing section
                        processingSection.style.display = 'none';
                        
                        // Show success section
                        successContainer.classList.add('show');
                        document.getElementById('successMessage').textContent = data.message;
                        downloadBtn.href = `/download/${taskId}`;
                        
                    } else if (data.status === 'error') {
                        // Hide processing section
                        processingSection.style.display = 'none';
                        
                        // Show error section
                        errorContainer.classList.add('show');
                        document.getElementById('errorMessage').textContent = data.message || data.error;
                        
                    } else {
                        // Continue polling
                        setTimeout(updateProgress, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error fetching progress:', error);
                    setTimeout(updateProgress, 2000);
                });
        }
        
        // Start progress polling
        setTimeout(updateProgress, 500);
    </script>
</body>
</html>"""
    
    with open('templates/processing.html', 'w') as f:
        f.write(processing_template)
    
    print("🚀 Starting PDF SKU Processor Web Server...")
    print("📂 Upload folder:", UPLOAD_FOLDER)
    print("🌐 Server will be available at: http://localhost:5000")
    print("🔄 Auto-opening browser in 1.5 seconds...")
    print("⚠️  Press Ctrl+C to stop the server")
    
    # Auto-open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run Flask app
    app.run(host='localhost', port=5000, debug=True, use_reloader=False)
