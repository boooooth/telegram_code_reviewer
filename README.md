# reviewbot

Telegram bot that reviews code (pasted snippets or GitHub PR links). Built on a LangGraph harness
with tiered memory (working/episodic/semantic) and a self-hosted Langfuse LLM-ops loop (tracing +
LLM-as-judge scoring).

## Status

Core review pipeline complete, plus a hardening pass on top:
- Telegram bot reviews pasted snippets and `/review <PR url>`
- Working memory (per-chat history via LangGraph's SQLite checkpointer)
- Episodic memory (every turn logged to `data/episodic.db`, indexed by chat for fast lookups)
- Semantic memory (Chroma + Google embeddings), auto-consolidated from episodic history every 5
  turns, deduped against existing facts before saving
- User-triggered memory management: `/new`, `/forget`, `/prune` (see Commands below)
- Guardrails (secret redaction, empty-response fallback)
- Langfuse tracing (self-hosted via Docker) — one trace per review with tokens/latency/cost
- LLM-as-judge scoring on every review, surfaced as a low-confidence flag in the Telegram reply
  when it scores below threshold (parse failures are logged, not silently swallowed)
- Graceful shutdown (drains in-flight reviews on SIGTERM/Ctrl+C)
- CI runs `pytest` and `mypy` on every push

## Setup

### 1. Python environment

```
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
```

### 2. Bot config

Copy `.env.example` to `.env` and fill in:
- `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `TELEGRAM_ALLOWED_USER_ID` — your numeric Telegram user id (e.g. from [@userinfobot](https://t.me/userinfobot)); the bot ignores everyone else
- An LLM API key matching `AGENT_MODEL_PROVIDER` (defaults to `google_genai` / `gemini-2.5-flash-lite` — set `GOOGLE_API_KEY`), or swap the provider/model and set the matching key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
- `GITHUB_TOKEN` — fine-grained PAT with `pull_requests: read`, only needed for private repos / higher rate limits

### 3. Langfuse (tracing + eval)

Requires Docker Desktop running.

```
.venv\Scripts\python.exe scripts\generate_langfuse_env.py
cd docker\langfuse
docker compose up -d
```

This generates `docker/langfuse/.env` with random secrets and auto-provisions an org/project/admin
user (no browser signup needed). The script prints `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` —
copy those into the project's `.env` along with `LANGFUSE_HOST=http://localhost:3000`.

If a host port in `docker/langfuse/docker-compose.yml` is already taken by something else on your
machine (the `postgres` service is currently mapped to `127.0.0.1:5433:5432` to avoid clashing with
a local Postgres install), edit the `ports:` line for that service to use a free host port instead
— this only changes the host-exposed port, not internal container-to-container communication.

Once running, the Langfuse dashboard is at `http://localhost:3000` (login: the email/password
`generate_langfuse_env.py` printed).

### 4. Run the bot

```
.venv\Scripts\python.exe -m reviewbot.main
```

In Telegram, message the bot a code snippet, `/review <github PR url>`, or use one of the commands
below. Typing `/` in the chat shows an autocomplete menu with all of them.

## Commands

| Command | What it does |
|---|---|
| `/review <PR url>` | Review a GitHub pull request |
| *(plain message)* | Review a pasted code snippet |
| `/new` | Clear working memory (current conversation context) — review history and learned facts are untouched |
| `/forget` | Clear all learned semantic facts about your codebase/preferences — review history and working memory are untouched |
| `/prune <days>` | Delete review history older than N days — learned facts and working memory are untouched |

## Swapping LLM providers

Change `AGENT_MODEL_PROVIDER`/`AGENT_MODEL_NAME` (and the matching API key) in `.env` — no code
changes needed. Provider values map to `init_chat_model`, e.g. `anthropic` + `claude-sonnet-4-5`,
`openai` + `gpt-5.1`, `google_genai` + `gemini-2.5-flash-lite`. `SUMMARIZER_MODEL_*` and
`JUDGE_MODEL_*` are configured the same way and can point at a cheaper model than the main agent.

## Tuning the reviewer

- `prompts/system_prompt.md` — base reviewer instructions
- `prompts/procedural/*.md` — additional conventions/rubric loaded into every review (edit or add files here)
- `src/reviewbot/observability/eval.py` — judge rubric and low-confidence threshold
- `src/reviewbot/memory/consolidation.py` — how often (and how) episodic history gets distilled into semantic facts

After changing a prompt, restart the bot to pick it up. Check Langfuse traces/scores at
`localhost:3000` to see whether a change actually improved review quality — that's the
diagnose/gate/release loop from the architecture doc, done by hand rather than automated.

## Development

```
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m mypy src
```

Both run automatically in CI (`.github/workflows/test.yml`) on every push and pull request.
