# Quick Start - Windows with VS Code

This guide will help you get the Speech-to-Text application running on Windows using Visual Studio Code.

## Prerequisites

Before you begin, ensure you have:
- ✅ **Windows 10 or 11**
- ✅ **Python 3.10 or newer** - [Download from python.org](https://www.python.org/downloads/)
- ✅ **Visual Studio Code** - [Download from code.visualstudio.com](https://code.visualstudio.com/)
- ✅ **Git** (optional, for cloning) - [Download from git-scm.com](https://git-scm.com/)

## Step 1: Install ffmpeg

**Choose one method:**

### Method A: Manual Installation (Recommended for beginners)

1. Download ffmpeg:
   - Visit: https://www.gyan.dev/ffmpeg/builds/
   - Download: **ffmpeg-release-essentials.zip**

2. Extract and install:
   - Extract the ZIP file
   - Rename the extracted folder to `ffmpeg`
   - Move it to `C:\` (you should have `C:\ffmpeg\bin\ffmpeg.exe`)

3. Add to PATH:
   - Press `Win + X` → Select "System"
   - Click "Advanced system settings" → "Environment Variables"
   - Under "System variables", find and edit "Path"
   - Click "New" → Add: `C:\ffmpeg\bin`
   - Click "OK" on all windows

4. Verify (in a **new** Command Prompt):
   ```cmd
   ffmpeg -version
   ```

### Method B: Using Chocolatey (For advanced users)

```powershell
choco install ffmpeg
```

## Step 2: Get the Code

### Option A: Using Git
```cmd
cd C:\Users\YourUsername\Documents
git clone https://github.com/nitinj8787/speech-to-text.git
cd speech-to-text
```

### Option B: Download ZIP
1. Download the repository as ZIP
2. Extract to a folder (e.g., `C:\Users\YourUsername\Documents\speech-to-text`)
3. Open the folder

## Step 3: Open in VS Code

1. Launch Visual Studio Code
2. File → Open Folder → Select the `speech-to-text` folder
3. Install the **Python extension** if prompted

## Step 4: Set Up Python Environment

### In VS Code Terminal (Ctrl + `)

```cmd
# Create virtual environment
python -m venv .venv

# Activate it (Command Prompt)
.venv\Scripts\activate

# OR activate it (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**Note:** First installation takes 5-10 minutes (downloads PyTorch ~1-2 GB)

### Configure VS Code Python Interpreter

1. Press `Ctrl + Shift + P`
2. Type: `Python: Select Interpreter`
3. Choose: `.venv\Scripts\python.exe`

## Step 5: Verify Installation

Run the test script:

```cmd
python test_setup.py
```

You should see:
```
🎉 All checks passed! Your environment is ready to use.
```

## Step 6: Run the Application

### Option A: Web Interface (Easiest)

1. Start the server:
   ```cmd
   python web_app.py
   ```

2. Open your browser to: http://localhost:5000

3. Drag and drop an audio file or click to browse

4. Click "Transcribe" and wait for results

### Option B: Command Line Interface

```cmd
# Basic usage
python app.py --input your_audio.mp3 --output transcription.txt

# With better accuracy (small model)
python app.py --input your_audio.mp3 --output transcription.txt --model small

# With timestamps
python app.py --input your_audio.mp3 --output transcription.txt --timestamps
```

## Common Issues and Solutions

### Issue: "Python not recognized"
**Solution:** Reinstall Python and check "Add Python to PATH" during installation

### Issue: "Cannot activate virtual environment"
**Solutions:**
- Command Prompt: `.venv\Scripts\activate.bat`
- PowerShell: `.venv\Scripts\Activate.ps1`
- If PowerShell gives error: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Issue: "ffmpeg not found"
**Solution:** See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed ffmpeg installation

### Issue: "ModuleNotFoundError"
**Solution:** Make sure virtual environment is activated (you see `(.venv)` in prompt)
```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: Slow transcription
**Solutions:**
- Use a smaller model: `--model tiny` or `--model base`
- Large files take time - be patient
- GPU helps (NVIDIA CUDA) but not required

## Tips for VS Code

### Recommended Extensions
- **Python** (Microsoft) - Already installed
- **Pylance** - Enhanced Python language support
- **GitLens** - Git integration (optional)

### Debugging

Create `.vscode\launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Web App",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/web_app.py",
      "console": "integratedTerminal"
    },
    {
      "name": "CLI App",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/app.py",
      "args": ["--input", "sample.mp3", "--output", "output.txt"],
      "console": "integratedTerminal"
    }
  ]
}
```

Press `F5` to start debugging.

### Terminal Shortcuts
- `Ctrl + `` - Toggle terminal
- `Ctrl + Shift + `` - New terminal
- `Ctrl + C` - Stop running process

## Performance Notes

### First Run
- Whisper model downloads on first use (~75 MB to 3 GB depending on model)
- Models are cached in `C:\Users\YourUsername\.cache\whisper`
- Subsequent runs are much faster

### Processing Speed
On a typical laptop (no GPU):
- **tiny model**: ~30 seconds for 5-min audio
- **base model**: ~1 minute for 5-min audio  
- **small model**: ~2-3 minutes for 5-min audio

With NVIDIA GPU (CUDA), processing is 5-10x faster.

## What's Next?

- Try different Whisper models (tiny, base, small, medium, large)
- Process different audio formats (MP3, WAV, M4A, etc.)
- Use timestamps for detailed transcription
- Experiment with different languages (auto-detect or specify with `--language en`)

## Need Help?

1. Check [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed troubleshooting
2. Run `python test_setup.py` to diagnose issues
3. See [README.md](README.md) for full documentation
4. Create an issue on GitHub with error details

---

**Happy transcribing! 🎙️ → 📝**
