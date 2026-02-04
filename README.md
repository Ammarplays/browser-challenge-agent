# 🤖 Browser Challenge Agent

Solves [Brett Adcock's 30 browser challenges](https://x.com/adcock_brett/status/2018417226895028414) in under 5 minutes using **Gemini 3 Flash Preview** + **Playwright**.

## Quick Start

```bash
# Clone
git clone https://github.com/AmmaarPlays/browser-challenge-agent.git
cd browser-challenge-agent

# Set your API key
export GEMINI_API_KEY="your-google-ai-key"

# Setup & run
make setup
make run
```

## Requirements

- Python 3.10+
- [Google AI API key](https://aistudio.google.com/apikey)
- 8GB+ RAM (Chromium is hungry)

## Commands

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies |
| `make run` | Run the agent |
| `make peek` | Preview the challenge site |
| `make clean` | Remove artifacts |
| `make run-custom MODEL=gemini-2.0-flash` | Use different model |

## How It Works

1. Opens the challenge site in headless Chromium
2. Screenshots each challenge
3. Sends to Gemini: "What action solves this?"
4. Executes the action (click, type, etc.)
5. Repeats until all 30 challenges are done

## Output

- `screenshots/` — Screenshots from each challenge
- `run_results.json` — Metrics (time, tokens, cost, success rate)

## Metrics Tracked

- Total time
- Challenges solved/failed
- Token usage (input/output)
- Estimated cost
- Actions taken

## Model Options

Default: `gemini-3-flash-preview` (best for agentic tasks)

Other options:
```bash
export GEMINI_MODEL="gemini-2.0-flash"      # Stable
export GEMINI_MODEL="gemini-2.5-flash"      # Balanced
export GEMINI_MODEL="gemini-3-flash-preview" # Latest (default)
```

## License

MIT
