# Document Generator with Ollama Cloud (DeepSeek-v3.2)

This project uses Ollama Cloud API with the model `deepseek-v3.2:cloud` to generate Python code that creates documents in various formats (txt, docx, pdf, xlsx, csv).

## Setup

1. Install Python 3.8 or higher
2. Run `setup.bat` to install dependencies
3. Run `run.bat` to start the web server
4. Open `http://localhost:5000` in your browser

## How it works

- You describe the desired content and select format
- The Flask app sends a prompt to Ollama Cloud API
- DeepSeek model generates Python code to create the file
- The code is executed in a temporary folder
- You download the resulting file

## API Key

The API key is already embedded in `app.py`. If you need to change it, edit the variable `OLLAMA_API_KEY`.

**Note:** Be cautious with generated code – it runs on your local machine.