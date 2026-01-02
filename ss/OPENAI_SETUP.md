# OpenAI Setup Guide for PersonaRAG

## Step 1: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to [API Keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Give your key a name (e.g., "PersonaRAG")
6. Copy the key (it will look like: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

## Step 2: Configure Your API Key

Edit the `.env` file in your project directory:

```bash
# Replace with your actual OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## Step 3: Restart the Application

1. Stop the current Flask server (Ctrl+C in the terminal)
2. Run: `python app.py`

## Step 4: Test the Integration

Once configured, the system will use OpenAI to generate persona-specific responses:

- **Executive**: Strategic, business-focused responses
- **Developer**: Technical, code-oriented responses  
- **HR Specialist**: People-focused, policy-aware responses
- **Student**: Educational, learning-focused responses
- **General**: Balanced, helpful responses

## Features

✅ **Persona-specific prompts** - Each role gets customized system prompts
✅ **Context-aware responses** - OpenAI understands the full conversation
✅ **Fallback system** - Works even if OpenAI is unavailable
✅ **Error handling** - Graceful handling of API issues

## Cost Considerations

- Uses `gpt-3.5-turbo` model (cost-effective)
- Maximum 1000 tokens per response
- Typical cost: ~$0.002 per 1K tokens
- You can monitor usage in your OpenAI dashboard

## Troubleshooting

If you see "OpenAI API key is not valid or missing":
1. Check your `.env` file has the correct key
2. Ensure no extra spaces or quotes around the key
3. Verify your key has active credits in your OpenAI account

If you see "OpenAI API rate limit exceeded":
1. Wait a few minutes and try again
2. Check your OpenAI usage limits
3. Consider upgrading your OpenAI plan

## Advanced Configuration

You can modify `openai_integration.py` to:
- Change the model (e.g., use `gpt-4` for higher quality)
- Adjust temperature (creativity level)
- Modify token limits
- Customize persona prompts
