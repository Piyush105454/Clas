// Optimized Mobile Camera Upload with Compression & Progress
(function() {
    'use strict';
    
    console.log('📷 Camera upload module loaded');
    
    const CONFIG = {
        MAX_FILE_SIZE: 2 * 1024 * 1024, // 2MB
        CHUNK_SIZE: 500 * 1024, // 500KB chunks
        MAX_RETRIES: 3,
        QUALITY: 0.8,
        TIMEOUT: 30000 // 30 seconds
    };
    
    // Wait for DOM to be ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }
    
    ready(function() {
        console.log('🔍 Initializing camera upload...');
        
        const btn = document.getElementById('lessonPlanCameraBtn');
        const input = document.getElementById('lessonPlanCameraInput');
        
        if (!btn || !input) {
            console.error('❌ Elements not found');
            return;
        }
        
        console.log('✓ Elements found');
        
        // Button click - open file picker
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('✓ Button clicked');
            input.click();
        });
        
        // File selected - compress then upload
        input.addEventListener('change', function(e) {
            if (!this.files || !this.files[0]) {
                console.log('No file selected');
                return;
            }
            
            const file = this.files[0];
            console.log('✓ File selected:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
            
            // Compress image first
            compressImage(file, function(compressedFile) {
                uploadFile(compressedFile);
            });
        });
        
        console.log('✓ Camera upload ready');
    });
    
    // Compress image using Canvas API
    function compressImage(file, callback) {
        const resultDiv = document.getElementById('uploadResult');
        
        if (!file.type.startsWith('image/')) {
            // Not an image, upload as-is
            callback(file);
            return;
        }
        
        resultDiv.innerHTML = '<div class="alert alert-info"><strong>📦 Compressing image...</strong></div>';
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Calculate new dimensions (max 2000px width)
                let width = img.width;
                let height = img.height;
                const maxWidth = 2000;
                
                if (width > maxWidth) {
                    height = (height * maxWidth) / width;
                    width = maxWidth;
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                // Convert to blob with quality setting
                canvas.toBlob(function(blob) {
                    const originalSize = (file.size / 1024 / 1024).toFixed(2);
                    const compressedSize = (blob.size / 1024 / 1024).toFixed(2);
                    
                    console.log(`✓ Compressed: ${originalSize}MB → ${compressedSize}MB`);
                    
                    // Create new file from blob
                    const compressedFile = new File([blob], file.name, {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    
                    resultDiv.innerHTML = `<div class="alert alert-success"><small>✓ Compressed: ${originalSize}MB → ${compressedSize}MB</small></div>`;
                    
                    callback(compressedFile);
                }, 'image/jpeg', CONFIG.QUALITY);
            };
            img.onerror = function() {
                console.error('Failed to load image');
                resultDiv.innerHTML = '<div class="alert alert-danger">Failed to compress image</div>';
                callback(file); // Fall back to original
            };
            img.src = e.target.result;
        };
        reader.onerror = function() {
            console.error('Failed to read file');
            callback(file); // Fall back to original
        };
        reader.readAsDataURL(file);
    }
    
    // Upload file with progress tracking
    function uploadFile(file) {
        const resultDiv = document.getElementById('uploadResult');
        const sessionId = document.querySelector('input[name="planned_session_id"]')?.value;
        
        if (!sessionId) {
            resultDiv.innerHTML = '<div class="alert alert-danger">❌ Error: Session not found</div>';
            return;
        }
        
        console.log('✓ Starting upload for session:', sessionId);
        
        // Show progress UI
        resultDiv.innerHTML = `
            <div class="alert alert-info">
                <div class="d-flex justify-content-between mb-2">
                    <strong>📤 Uploading...</strong>
                    <span id="uploadPercent">0%</span>
                </div>
                <div class="progress" style="height: 20px;">
                    <div id="uploadBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%"></div>
                </div>
                <small id="uploadSpeed" class="text-muted d-block mt-2">Calculating speed...</small>
                <button id="cancelUploadBtn" class="btn btn-sm btn-outline-danger mt-2">Cancel</button>
            </div>
        `;
        
        const formData = new FormData();
        formData.append('lesson_plan_file', file);
        formData.append('planned_session_id', sessionId);
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        const xhr = new XMLHttpRequest();
        let startTime = Date.now();
        let lastTime = startTime;
        let lastLoaded = 0;
        
        // Progress tracking
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                const currentTime = Date.now();
                const timeDiff = (currentTime - lastTime) / 1000; // seconds
                const bytesDiff = e.loaded - lastLoaded;
                const speed = (bytesDiff / timeDiff / 1024 / 1024).toFixed(2); // MB/s
                
                document.getElementById('uploadPercent').textContent = Math.round(percentComplete) + '%';
                document.getElementById('uploadBar').style.width = percentComplete + '%';
                document.getElementById('uploadSpeed').textContent = `Speed: ${speed} MB/s`;
                
                lastTime = currentTime;
                lastLoaded = e.loaded;
            }
        });
        
        // Cancel button
        document.getElementById('cancelUploadBtn').addEventListener('click', function() {
            xhr.abort();
            resultDiv.innerHTML = '<div class="alert alert-warning">⏸️ Upload cancelled</div>';
        });
        
        // Completion
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        resultDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>✓ Uploaded successfully!</div>';
                        
                        const form = document.getElementById('lessonPlanUploadForm');
                        if (form) form.style.display = 'none';
                        
                        const completed = document.getElementById('uploadCompletedSection');
                        if (completed) {
                            completed.style.display = 'block';
                            setTimeout(() => completed.scrollIntoView({ behavior: 'smooth' }), 300);
                        }
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${data.error}</div>`;
                    }
                } catch (e) {
                    resultDiv.innerHTML = '<div class="alert alert-danger">❌ Upload failed: Invalid response</div>';
                }
            } else {
                resultDiv.innerHTML = `<div class="alert alert-danger">❌ Upload failed: HTTP ${xhr.status}</div>`;
            }
        });
        
        // Error handling
        xhr.addEventListener('error', function() {
            resultDiv.innerHTML = '<div class="alert alert-danger">❌ Network error. Please check your connection.</div>';
        });
        
        xhr.addEventListener('abort', function() {
            console.log('Upload aborted');
        });
        
        // Timeout
        xhr.timeout = CONFIG.TIMEOUT;
        xhr.addEventListener('timeout', function() {
            resultDiv.innerHTML = '<div class="alert alert-danger">❌ Upload timeout. Please try again.</div>';
        });
        
        // Send
        xhr.open('POST', '/api/upload-lesson-plan/', true);
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
        xhr.send(formData);
    }
})();
