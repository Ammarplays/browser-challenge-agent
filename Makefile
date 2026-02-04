# Browser Challenge Agent
# Solves 30 browser challenges in <5 minutes using Gemini 3 Flash + Playwright

.PHONY: setup run run-verbose peek clean help

help:
	@echo "Browser Challenge Agent"
	@echo "======================="
	@echo ""
	@echo "  make setup     - Install dependencies (first time)"
	@echo "  make run       - Run the agent (verbose, shows actions)"
	@echo "  make run-quiet - Run with minimal output"
	@echo "  make peek      - Preview the challenge site"
	@echo "  make clean     - Remove venv and artifacts"
	@echo ""
	@echo "Quick start:"
	@echo "  export GEMINI_API_KEY='your-key'"
	@echo "  make setup"
	@echo "  make run"

# Create venv and install dependencies
setup:
	@echo "Setting up environment..."
	@python3 -m venv venv
	@./venv/bin/pip install --upgrade pip
	@./venv/bin/pip install playwright google-generativeai
	@./venv/bin/playwright install chromium --with-deps
	@mkdir -p screenshots
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next: export GEMINI_API_KEY='your-key' && make run"

# Run the agent (verbose by default)
run:
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "❌ GEMINI_API_KEY not set"; \
		echo "Run: export GEMINI_API_KEY='your-key'"; \
		exit 1; \
	fi
	@./venv/bin/python agent.py --verbose

# Run with minimal output (no action details)
run-quiet:
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "❌ GEMINI_API_KEY not set"; \
		exit 1; \
	fi
	@./venv/bin/python agent.py

# Preview the challenge site
peek:
	@./venv/bin/python peek.py
	@echo "📸 Screenshot saved to challenge_preview.png"

# Clean up
clean:
	@rm -rf venv screenshots *.png run_results.json __pycache__
	@echo "🧹 Cleaned"

# Run with custom model
run-custom:
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "❌ GEMINI_API_KEY not set"; \
		exit 1; \
	fi
	@if [ -z "$(MODEL)" ]; then \
		echo "Usage: make run-custom MODEL=gemini-2.0-flash"; \
		exit 1; \
	fi
	@GEMINI_MODEL=$(MODEL) ./venv/bin/python agent.py
