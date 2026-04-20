# Portkey Gateway Demo

Interactive demos for [Portkey's](https://portkey.ai) three gateways — **AI Gateway**, **MCP Gateway**, and **Agent Gateway**. Includes runnable Jupyter notebooks and a live web tester.

## What's Inside

```
DemoDirectory/
├── portkey_ai_gateway_demo.ipynb      # AI Gateway — 12 features live
├── portkey_mcp_gateway_demo.ipynb     # MCP Gateway — build, register, call
├── portkey_agent_gateway_demo.ipynb   # Agent Gateway — 6 frameworks
├── web_tester/                        # Interactive web UI
│   ├── app.py                         #   FastAPI backend
│   ├── index.html                     #   Single-page frontend
│   └── requirements.txt               #   Python dependencies
└── .env                               # PORTKEY_API_KEY (not committed)
```

## Prerequisites

- Python 3.9+
- A [Portkey account](https://app.portkey.ai) with an API key
- At least one [virtual key](https://app.portkey.ai/virtual-keys) configured for your LLM provider

## Quick Start

### 1. Clone & configure

```bash
git clone <repo-url> && cd DemoDirectory
echo "PORTKEY_API_KEY=your-key-here" > .env
```

### 2. Run the notebooks

```bash
pip install portkey-ai jupyter
jupyter notebook
```

Open any of the three `.ipynb` files. Each notebook is self-contained with setup instructions at the top.

### 3. Run the web tester

```bash
cd web_tester
pip install -r requirements.txt
python3 app.py
```

Open **http://localhost:5005** — paste your API key, set your models, and start testing.

## Notebooks

### AI Gateway (`portkey_ai_gateway_demo.ipynb`)

One SDK, one API key, 250+ LLM providers. Covers:

| Feature | What it does |
|---------|-------------|
| Chat Completions | OpenAI-compatible interface for any provider |
| Fallbacks | Auto-switch to backup LLMs on failure |
| Automatic Retries | Exponential backoff on 429/500/503 |
| Caching | Simple & semantic — serve repeated requests 20x faster |
| Load Balancing | Weighted traffic distribution across models |
| Conditional Routing | Route by user plan, metadata, or model alias |
| Canary Testing | Test new models on a percentage of traffic |
| Streaming | Real-time token streaming with all features intact |
| Guardrails | Input/output validation at the gateway edge |
| Metadata & Tracing | Tag and trace every request in the dashboard |
| Nested Strategies | Compose fallback + LB + retry + cache in one config |

**Default models:**
- Primary: `@anthropic/claude-sonnet-4-6`
- Backup: `@hk-openrouter/meta-llama/llama-3.3-70b-instruct`

### MCP Gateway (`portkey_mcp_gateway_demo.ipynb`)

Centralized proxy between MCP clients and MCP servers. Covers:

| Feature | What it does |
|---------|-------------|
| Build MCP Server | Create a FastMCP server with tools, resources, and prompts |
| Register with Portkey | Add servers to the MCP Registry via REST API |
| List & Call Tools | Discover and execute tools through the gateway |
| Client Configs | Generate configs for Claude Desktop, Cursor, and VS Code |
| AI Gateway Integration | Combine MCP tools with fallbacks, caching, and routing |

### Agent Gateway (`portkey_agent_gateway_demo.ipynb`)

Make any agent framework production-ready. Covers:

| Framework | Integration |
|-----------|-----------|
| OpenAI Agents SDK | Native Portkey client as LLM provider |
| LangChain / LangGraph | ChatOpenAI through Portkey, graph-based agent |
| CrewAI | Multi-agent crew routed through the gateway |
| Strands Agents | PortkeyStrands adapter |
| Google ADK | PortkeyAdk adapter |
| Auto-Instrumentation | OpenTelemetry-based, zero-code observability |

## Web Tester

A browser-based UI for testing AI Gateway and MCP Gateway features interactively.

**Stack:** FastAPI + vanilla HTML/JS with the Portkey Luna theme (Nord Arctic Night).

**AI Gateway tab** — 9 test panels: Chat, Streaming, Fallback, Retry, Caching, Load Balancing, Conditional Routing, Guardrails, Metadata & Tracing, Nested Strategies.

**MCP Gateway tab** — 6 test panels: List Integrations, Register Server, List Tools, Call Tool, Delete Integration, Client Config Generator.

### Running the web tester

```bash
cd web_tester
pip install -r requirements.txt

# Option A: direct
python3 app.py

# Option B: with auto-reload
uvicorn app:app --host 0.0.0.0 --port 5005 --reload
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORTKEY_API_KEY` | Yes | Your Portkey API key from [app.portkey.ai](https://app.portkey.ai) |

Create a `.env` file in the `DemoDirectory/` root. The web tester and notebooks both read from it.

## Links

- [Portkey Docs](https://portkey.ai/docs)
- [Portkey Dashboard](https://app.portkey.ai)
- [AI Gateway (GitHub)](https://github.com/Portkey-AI/gateway)
- [Python SDK](https://github.com/Portkey-AI/portkey-python-sdk)

## License

Internal demo — not for redistribution.
