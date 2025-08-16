# 🔧 PythonAnywhere I/O Fix Guide

## 🚨 Problem
Getting error: `"Error processing PDF: [Errno 11] write could not complete without blocking"`

This is a common issue on PythonAnywhere related to non-blocking I/O operations.

## ✅ Quick Fix

### Option 1: Replace flask_app.py (Recommended)
1. **Download** the updated `pdf_processor_pythonanywhere_fixed.tar.gz`
2. **Extract** and copy the new `flask_app.py` to your `/home/yourusername/mysite/` directory
3. **Reload** your web app in PythonAnywhere Web tab

### Option 2: Manual Fix in PythonAnywhere Console
Run these commands in your PythonAnywhere console:

```bash
cd ~/mysite

# Backup current flask_app.py
cp flask_app.py flask_app.py.backup

# Create the fixed version
cat > flask_app.py << 'EOF'
# Add the import fixes at the top after existing imports
import errno
import fcntl

# Replace the UPLOAD_FOLDER line with:
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Add this function after the processing_status = {} line:
def safe_file_save(file_obj, filepath, max_retries=3):
    """Safely save uploaded file with retry logic for PythonAnywhere"""
    for attempt in range(max_retries):
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save file with explicit binary mode and buffering
            with open(filepath, 'wb') as f:
                # Read file in chunks to avoid blocking
                chunk_size = 8192
                while True:
                    chunk = file_obj.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    f.flush()  # Force write to disk
                    os.fsync(f.fileno())  # Ensure data is written
            
            # Reset file pointer for potential re-use
            file_obj.seek(0)
            return True
            
        except (IOError, OSError) as e:
            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                # Resource temporarily unavailable, retry
                time.sleep(0.1 * (attempt + 1))
                continue
            else:
                raise e
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(0.1 * (attempt + 1))
    
    return False
EOF

# Then replace the file.save(filepath) line in upload_file() with:
# Use safe file saving method
#         try:
#             if not safe_file_save(file, filepath):
#                 flash('Failed to save uploaded file. Please try again.', 'error')
#                 return redirect(url_for('index'))
#         except Exception as e:
#             flash(f'Error saving file: {str(e)}', 'error')
#             return redirect(url_for('index'))
```

## 🔄 After Applying Fix

1. **Go to Web tab** in PythonAnywhere dashboard
2. **Click "Reload"** button 
3. **Test your app** - the blocking error should be resolved

## 🧪 Test the Fix

1. **Upload a sample PDF** 
2. **Check for successful processing**
3. **Verify download works**

## 💡 What This Fix Does

- **Chunked file reading**: Prevents large file blocking
- **Retry logic**: Handles temporary resource unavailability  
- **Explicit flush/sync**: Ensures data is written to disk
- **Better error handling**: More informative error messages
- **Directory creation**: Ensures upload folders exist

## 🆘 If Still Having Issues

1. **Check error logs** in PythonAnywhere Web tab
2. **Verify file permissions**: `chmod 755 ~/mysite/*.py`
3. **Check disk space**: `df -h` in console
4. **Try smaller PDF files** first

The updated version should resolve the blocking I/O issues commonly seen on shared hosting platforms like PythonAnywhere!
