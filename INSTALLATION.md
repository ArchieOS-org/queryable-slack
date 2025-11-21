# Installation Guide

## Required Dependencies

### Core Dependencies (Always Required)
```bash
pip install -r requirements.txt
```

### Optional Dependencies for Full Functionality

#### FFmpeg (for video processing)
```bash
# Install FFmpeg binary (required for video frame extraction and audio extraction)
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### Lightning Whisper MLX (for audio transcription)
```bash
# Note: This requires Rust compiler. If installation fails:
# 1. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 2. Or use pre-built wheels if available
pip install lightning-whisper-mlx
```

## Verification

Run tests to verify installation:
```bash
pytest tests/ -v -s
```

## What Works Without Optional Dependencies

- ✅ Text file processing (CSV, XLSX, PPTX, PDF, DOCX, TXT, ZIP)
- ✅ File type queries (with prominent labeling fix)
- ✅ ChromaDB queries and semantic search
- ✅ Metadata extraction for all file types
- ⚠️ Video processing: Will return metadata only (no frame extraction/transcription)
- ⚠️ Audio processing: Will return metadata only (no transcription)

## System Requirements

- **macOS** (Apple Silicon recommended for MLX)
- **Python 3.11, 3.12, or 3.13**
- **32GB RAM** (for full dataset processing)
- **FFmpeg** (for video/audio processing)

