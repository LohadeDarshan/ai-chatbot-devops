import os
import httpx

# Ollama runs as its own container/pod and exposes an HTTP API.
# OLLAMA_HOST and OLLAMA_MODEL are injected via env vars / ConfigMap.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

TIMEOUT = httpx.Timeout(60.0)


async def generate_reply(prompt: str) -> str:
    """
    Send the user's message to the open-source LLM served by Ollama
    and return the generated text reply.

    If Ollama is unreachable (e.g. still downloading the model on first
    run), fall back to a friendly message instead of crashing the API.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip() or "(empty response from model)"
    except httpx.ConnectError:
        return (
            "⚠️ AI model server (Ollama) is not reachable yet. "
            "It may still be starting up or pulling the model. Try again in a minute."
        )
    except httpx.HTTPStatusError as e:
        return f"⚠️ Model server returned an error: {e.response.status_code}"
    except Exception as e:
        return f"⚠️ Unexpected error talking to model server: {e}"
