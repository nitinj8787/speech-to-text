# Windows Setup Guide

This guide helps you resolve common issues when running the Speech-to-Text application on Windows.

## Common Error: pydub/ffmpeg not found

If you see an error like:
```
File "...\pydub\utils.py", line 14, in <module>
FileNotFoundError: [WinError 2] The system cannot find the file specified
```

This means **ffmpeg is not installed or not found** by the application.

## Solution: Install and Configure ffmpeg

### Option 1: Download and Add to PATH (Recommended)

1. **Download ffmpeg for Windows:**
   - Visit: https://ffmpeg.org/download.html
   - Click on "Windows builds from gyan.dev"
   - Download the "ffmpeg-release-essentials.zip"

2. **Extract ffmpeg:**
   - Extract the downloaded ZIP file
   - Move the extracted folder to `C:\ffmpeg\`
   - You should now have files at: `C:\ffmpeg\bin\ffmpeg.exe`

3. **Add to System PATH:**
   - Open "Edit the system environment variables" (search in Windows Start menu)
   - Click "Environment Variables"
   - Under "System variables", find and select "Path"
   - Click "Edit"
   - Click "New"
   - Add: `C:\ffmpeg\bin`
   - Click "OK" on all windows

4. **Verify installation:**
   - Open a **NEW** Command Prompt or PowerShell window
   - Run: `ffmpeg -version`
   - You should see ffmpeg version information

5. **Restart VS Code** if it was already open

### Option 2: Use Chocolatey Package Manager (Easier)

If you have [Chocolatey](https://chocolatey.org/) installed:

```powershell
choco install ffmpeg
```

Then restart your terminal/VS Code.

### Option 3: Place ffmpeg in a Known Location

The application automatically checks these Windows locations:

- `C:\WorkspaceNj\ffmpeg-8.1\bin\ffmpeg.exe`
- `C:\ffmpeg\bin\ffmpeg.exe`
- `C:\Program Files\ffmpeg\bin\ffmpeg.exe`

Simply place ffmpeg in one of these directories (we recommend `C:\ffmpeg\bin\`).

## After Installing ffmpeg

1. **Restart your terminal/VS Code**
2. **Activate your virtual environment:**
   ```cmd
   .venv\Scripts\activate
   ```

3. **Test the application:**
   ```cmd
   python app.py --help
   ```
   or
   ```cmd
   python web_app.py
   ```

## Still Having Issues?

### Check if ffmpeg is accessible:
```cmd
where ffmpeg
```

This should show the path to ffmpeg.exe. If it doesn't, ffmpeg is not in your PATH.

### Manual verification:
```cmd
C:\ffmpeg\bin\ffmpeg.exe -version
```

If this works but `ffmpeg -version` doesn't, then PATH is not configured correctly.

### Python verification:
```python
python -c "from pydub import AudioSegment; print('pydub configured successfully')"
```

## Additional Windows-Specific Tips

### Virtual Environment Activation Issues

If `.venv\Scripts\activate` doesn't work:
- Try: `.venv\Scripts\Activate.ps1` (PowerShell)
- Or: `.venv\Scripts\activate.bat` (Command Prompt)

### Execution Policy Error (PowerShell)

If you get "execution policy" errors in PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Permission Errors

Run VS Code or Command Prompt as Administrator if you encounter permission issues.

## Testing Your Setup

The repository includes a test script to verify your environment. Simply run:

```cmd
python test_setup.py
```

This script will check:
- ✓ Python version (3.10+ required)
- ✓ Virtual environment activation
- ✓ pydub installation
- ✓ ffmpeg availability
- ✓ OpenAI Whisper installation
- ✓ Flask installation
- ✓ NumPy installation

If all checks pass, you'll see:
```
🎉 All checks passed! Your environment is ready to use.
```

If any checks fail, the script provides specific guidance on how to fix the issue.

## Need More Help?

Create an issue on GitHub with:
- The exact error message
- Output of `python --version`
- Output of `where ffmpeg` (or "not found" if it doesn't work)
- Your Windows version
