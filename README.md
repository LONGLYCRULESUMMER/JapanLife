# JapanLife - 在日外国人智能助手

Multi-agent AI assistant for foreigners living in Japan, built with Google ADK + Claude.

## Quick Start

```bash
# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Ingest knowledge base
make ingest

# Run dev server
make serve
```
