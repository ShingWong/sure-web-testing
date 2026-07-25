# Vision Provider Configuration

Configure vision analysis via environment variables. All models are accessible through one of three providers.

## Provider Comparison

| Provider | Cost/1K images | Quality | Setup |
|----------|---------------|---------|-------|
| **OpenRouter (Qwen)** | ~$0.05 | Good | API key at openrouter.ai |
| **OpenRouter (GLM)** | ~$0.08 | Good | Same key |
| **Google Gemini** | Free tier | Good | API key at aistudio.google.com |
| **OpenAI GPT-4o** | ~$2.50 | Best | API key at platform.openai.com |

## Quick Configs

### Qwen 3.6 (cheapest, recommended)
```bash
export VISION_PROVIDER=openrouter
export VISION_MODEL=qwen/qwen3.6-plus
export OPENROUTER_API_KEY=sk-or-v1-...
pip install "agentic-web-testing[openrouter-vision]"
```

### GLM-4V-Plus (good Chinese/English)
```bash
export VISION_PROVIDER=openrouter
export VISION_MODEL=glm-4v-plus
export OPENROUTER_API_KEY=sk-or-v1-...
```

### Gemini 2.5 Flash Lite (free tier)
```bash
export VISION_PROVIDER=google
export VISION_MODEL=gemini-2.5-flash-lite
export GOOGLE_API_KEY=AIza...
pip install "agentic-web-testing[google-vision]"
```

### GPT-4o (best quality)
```bash
export VISION_PROVIDER=openai
export VISION_MODEL=gpt-4o
export OPENAI_API_KEY=sk-proj-...
pip install "agentic-web-testing[openai-vision]"
```

### Other OpenRouter models
```bash
export VISION_PROVIDER=openrouter
# Any vision model from https://openrouter.ai/models
export VISION_MODEL=qwen/qwen3.6-plus       # or...
export VISION_MODEL=google/gemini-2.5-flash-lite  # or...
export VISION_MODEL=anthropic/claude-3.5-sonnet  # or...
export VISION_MODEL=meta-llama/llama-3.2-11b-vision
export OPENROUTER_API_KEY=sk-or-v1-...
```

### Custom OpenAI-compatible endpoint (vLLM, Ollama, etc.)
```bash
export VISION_PROVIDER=openai
export VISION_BASE_URL=http://localhost:8000/v1
export VISION_API_KEY=not-needed  # or your local key
```

## Verify It Works

```bash
# Start the server
python -m src.server

# In another terminal, send a test request:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"analyze_screenshot","arguments":{"prompt":"Describe what you see"}}}' | nc localhost 8080
```
