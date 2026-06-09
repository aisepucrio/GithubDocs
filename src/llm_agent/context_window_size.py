LLM_CONTEXT_WINDOWS = {
    # --- Gemini ---
    "gemini-2.5-pro": 1_048_576,
    "gemini-2.5-flash": 1_048_576,
    "gemini-3.5-flash": 1_048_576,
    "gemini-2.5-flash-lite": 1_048_576,
    "gemini-2.0-flash-lite": 1_048_576,
    "gemini-2.0-flash": 1_048_576,

    # --- GPT ---
    "gpt-5-2025-08-07": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-mini-2025-08-07": 400_000,
    "gpt-5-nano": 400_000,
    "gpt-5-nano-2025-08-07": 400_000,

    # --- Llama 3.x (Ollama) ---
    "llama3.1:latest": 128_000,
    "llama3.1:8b": 128_000,
    "llama3.1:70b": 128_000,
    "llama3.2:latest": 128_000,
    "llama3.2:3b": 128_000,
    "llama3.3:latest": 128_000,

    # --- Mistral / Mixtral (Ollama) ---
    "mistral:latest": 32_768,
    "mistral-nemo:latest": 128_000,
    "mixtral:latest": 32_768,
    "mixtral:8x7b": 32_768,

    # --- Qwen (Ollama) ---
    "qwen2.5:latest": 128_000,
    "qwen2.5:7b": 128_000,
    "qwen2.5-coder:latest": 128_000,
    "qwen3-coder:30b": 262_144,

    # --- Google Gemma (Ollama) ---
    "gemma3:latest": 128_000,
    "gemma3:4b": 128_000,
    "gemma2:latest": 8_192,
    "gemma4:31b": 256_000,

    # --- DeepSeek (Ollama) ---
    "deepseek-r1:latest": 64_000,
    "deepseek-r1:7b": 64_000,

    # --- Microsoft Phi (Ollama) ---
    "phi4:latest": 16_384,
    "phi4-mini:latest": 16_384,

    # --- Meta CodeLlama (Ollama) ---
    "codellama:latest": 16_384,

    # --- NVIDIA Nemotron (Ollama) ---
    "nemotron-cascade-2:30b": 256_000,

    # --- Mock ---
    "mock": 10_000_000_000_000,
}