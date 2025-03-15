// static/scripts.js
let fileId = null;
let translationId = null;

// File upload enhancements
const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('formFile');
const browseBtn = document.getElementById('browseBtn');
const fileName = document.getElementById('fileName');

// Error handling function - displays errors in the UI
function displayErrorMessage(message, container) {
    // Create error element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger mt-3';
    errorDiv.textContent = message;

    // Remove any existing error messages
    const existingErrors = container.querySelectorAll('.alert-danger');
    existingErrors.forEach(el => el.remove());

    // Add error message to container
    container.appendChild(errorDiv);

    // Auto-remove after 8 seconds
    setTimeout(() => errorDiv.remove(), 2000);
}

// Progress update function - shows detailed status
function updateProgressStatus(message, percent, statusElement, progressBar) {
    statusElement.innerHTML = `<strong>${message}</strong>`;
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
}

// Reset UI to initial state
function resetUploadUI() {
    document.querySelector('.file-upload').style.display = 'block';
    document.querySelector('.progress-container').style.display = 'none';
    document.querySelector('.subtitle-actions').style.display = 'none';
}

browseBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', function () {
    if (this.files && this.files[0]) {
        fileName.textContent = this.files[0].name;
        fileName.style.display = 'block';
        dropArea.classList.add('border-primary');
    }
});

// Drag and drop functionality
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropArea.classList.add('border-primary');
    dropArea.style.backgroundColor = 'rgba(67, 97, 238, 0.05)';
}

function unhighlight() {
    dropArea.classList.remove('border-primary');
    dropArea.style.backgroundColor = '';
}

dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    fileInput.files = files;

    if (files && files[0]) {
        fileName.textContent = files[0].name;
        fileName.style.display = 'block';
    }
}

document.getElementById('uploadForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const file = fileInput.files[0];
    const uploadContainer = document.querySelector('.file-upload').parentElement;

    if (!file) {
        displayErrorMessage('Please select a file to upload', uploadContainer);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    const language = document.getElementById('language').value;
    formData.append('language', language);

    // Show progress indicator
    document.querySelector('.file-upload').style.display = 'none';
    document.querySelector('.progress-container').style.display = 'block';
    document.querySelector('.subtitle-actions').style.display = 'none';

    const statusElement = document.getElementById('statusMessage');
    const progressBar = document.querySelector('.progress-bar');

    updateProgressStatus('Uploading your file...', 10, statusElement, progressBar);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error (${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }

            fileId = data.file_id;
            updateProgressStatus('File uploaded successfully, processing...', 20, statusElement, progressBar);

            // Start polling for status updates
            pollTaskStatus(fileId);
        })
        .catch(error => {
            console.error('Error:', error);
            resetUploadUI();
            displayErrorMessage(`Upload failed: ${error.message}`, uploadContainer);
        });
});

function pollTaskStatus(id) {
    const progressContainer = document.querySelector('.progress-container');
    const statusElement = document.getElementById('statusMessage');
    const progressBar = document.querySelector('.progress-bar');
    const uploadContainer = progressContainer.parentElement;

    fetch(`/status/${id}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error (${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Update status message and progress bar
            updateProgressStatus(data.status, data.progress, statusElement, progressBar);

            if (data.state === 'SUCCESS') {
                // Processing completed
                document.querySelector('.progress-container').style.display = 'none';
                document.querySelector('.subtitle-actions').style.display = 'block';

                // Set up download link
                document.getElementById('downloadBtn').href = `/download/${fileId}`;
            } else if (data.state === 'FAILURE') {
                throw new Error(data.status || 'Processing failed');
            } else {
                // Still processing, poll again after a delay
                setTimeout(() => pollTaskStatus(id), 5000);
            }
        })
        .catch(error => {
            console.error('Status check error:', error);
            resetUploadUI();
            displayErrorMessage(`Processing error: ${error.message}`, uploadContainer);
        });
}

document.getElementById('translateBtn').addEventListener('click', function () {
    const targetLanguage = document.getElementById('targetLanguage').value;
    const translationContainer = document.querySelector('.subtitle-actions');

    document.getElementById('translationStatus').style.display = 'block';
    document.getElementById('translationResult').style.display = 'none';

    const translationStatusElem = document.getElementById('translationStatus');
    translationStatusElem.innerHTML = '<div class="spinner-border text-primary" role="status"></div> <span>Starting translation...</span>';

    fetch('/translate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            file_id: fileId,
            target_language: targetLanguage
        }),
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error (${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }

            translationId = data.translation_id;
            translationStatusElem.innerHTML = '<div class="spinner-border text-primary" role="status"></div> <span>Translation in progress...</span>';
            pollTranslationStatus(translationId);
        })
        .catch(error => {
            console.error('Translation request error:', error);
            document.getElementById('translationStatus').style.display = 'none';
            displayErrorMessage(`Translation request failed: ${error.message}`, translationContainer);
        });
});

function pollTranslationStatus(id) {
    const translationContainer = document.querySelector('.subtitle-actions');
    const translationStatusElem = document.getElementById('translationStatus');

    fetch(`/status/${id}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error (${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Update translation status
            if (data.status) {
                translationStatusElem.innerHTML = `<div class="spinner-border text-primary" role="status"></div> <span>${data.status} (${data.progress}%)</span>`;
            }

            if (data.state === 'SUCCESS') {
                // Translation completed
                document.getElementById('translationStatus').style.display = 'none';
                document.getElementById('translationResult').style.display = 'block';

                // Set up translated download link
                document.getElementById('downloadTranslationBtn').href = `/download/${id}`;
            } else if (data.state === 'FAILURE') {
                throw new Error(data.status || 'Translation failed');
            } else {
                // Still processing, poll again after a delay
                setTimeout(() => pollTranslationStatus(id), 5000);
            }
        })
        .catch(error => {
            console.error('Translation status error:', error);
            document.getElementById('translationStatus').style.display = 'none';
            displayErrorMessage(`Translation error: ${error.message}`, translationContainer);
        });
}

document.addEventListener('DOMContentLoaded', function () {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.querySelector('.theme-icon i');

    // Check for saved theme preference or use device preference
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");
    const savedTheme = localStorage.getItem("theme");

    // Set initial state based on saved preference or system preference
    if (savedTheme === "dark" || (!savedTheme && prefersDarkScheme.matches)) {
        document.body.classList.add("dark-mode");
        themeToggle.checked = true;
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    }

    // Listen for toggle changes
    themeToggle.addEventListener('change', function () {
        if (this.checked) {
            // Switch to dark mode
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            // Switch to light mode
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    });
});
