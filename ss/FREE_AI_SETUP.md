# 🆓 Free AI Setup Guide

## Option 1: Use Ollama (Recommended - Completely Free)

### Step 1: Install Ollama
1. Go to https://ollama.ai
2. Download and install Ollama for your operating system
3. Restart your computer after installation

### Step 2: Download a Free AI Model
Open Command Prompt/PowerShell and run:
```bash
ollama pull llama3.2
```

### Step 3: Start Ollama
```bash
ollama serve
```

### Step 4: Test Your Setup
Your system will automatically use the free local AI!

---

## Option 2: Use Free OpenAI Credits

### Step 1: Sign up for OpenAI
1. Go to https://platform.openai.com/signup
2. Create a new account
3. New accounts often get $5-18 in free credits

### Step 2: Get API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (starts with "sk-")

### Step 3: Update .env File
Replace the API key in your `.env` file

---

## Option 3: Use Google Gemini (Free)

### Step 1: Get Gemini API Key
1. Go to https://makersuite.google.com/app/apikey
2. Create a free API key
3. Copy the key

### Step 2: Update Configuration
(Requires additional setup - contact me for implementation)

---

## 🚀 Quick Start with Ollama (Easiest)

1. **Install Ollama**: https://ollama.ai
2. **Run in terminal**: `ollama pull llama3.2`
3. **Start server**: `ollama serve`
4. **Your system is ready!** ✅

## 📊 Model Options

### Free Models Available:
- `llama3.2` (3.8B) - Fast, good for general chat
- `llama3.2:1b` (1B) - Very fast, basic responses
- `qwen2.5:1.5b` - Good for technical topics
- `gemma2:2b` - Google's free model

### Download Models:
```bash
ollama pull llama3.2:1b    # Very fast
ollama pull qwen2.5:1.5b   # Technical
ollama pull gemma2:2b      # Google model
```

## 🔧 Configuration

### To Change Models:
Edit `.env` file:
```
LOCAL_MODEL=llama3.2:1b    # Use 1B model (faster)
LOCAL_MODEL=qwen2.5:1.5b   # Use technical model
```

### To Disable Local AI:
Edit `.env` file:
```
USE_LOCAL_AI=false
```

## 💡 Benefits of Local AI

✅ **Completely Free** - No API costs  
✅ **Private** - Data stays on your computer  
✅ **Fast** - No internet delays  
✅ **Always Available** - No quota limits  
✅ **Customizable** - Use different models  

## 🎯 Recommended Setup

**For best performance:**
```bash
# Install the 1B model (fastest for chat)
ollama pull llama3.2:1b

# Update .env file
LOCAL_MODEL=llama3.2:1b
```

This gives you instant, free AI responses! 🚀
