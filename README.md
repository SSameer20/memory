# memory

## Setup

First install the dependencies inside `app` folder
`pip install -r requirements.txt`

then run the server using
`uvicorn app.main:app --reload`

## LLM provider

The app now uses a provider abstraction for LLM access.

Current default:

- `LLM_PROVIDER=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-5.6-terra`

Example:

```bash
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-5.6-terra"
```

The provider is selected through `app.services.get_llm_provider()`, so other LLM backends can be added without changing the call sites.
