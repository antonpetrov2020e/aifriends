.PHONY: help install run clean test format lint

help: ## Show this help message
	@echo "AI Friends Bot - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

run: ## Run the bot
	@echo "Starting AI Friends Bot..."
	python -m src.main

dev: ## Run in development mode with auto-reload
	@echo "Starting AI Friends Bot in dev mode..."
	DEBUG=True python -m src.main

clean: ## Clean up generated files
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf build dist
	@echo "✅ Cleaned!"

clean-db: ## Delete database (reset all data)
	@echo "⚠️  Deleting database..."
	rm -f aifriends.db
	rm -rf chroma_db/
	@echo "✅ Database deleted. Fresh start on next run."

test: ## Run tests (when implemented)
	@echo "Running tests..."
	pytest tests/ -v

format: ## Format code with black
	@echo "Formatting code..."
	black src/
	@echo "✅ Code formatted!"

lint: ## Lint code with flake8
	@echo "Linting code..."
	flake8 src/ --max-line-length=100
	@echo "✅ Linting complete!"

setup: ## Initial setup (install + create .env)
	@echo "Setting up AI Friends Bot..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env file created. Please edit it with your tokens."; \
	else \
		echo "⚠️  .env already exists. Skipping."; \
	fi
	make install
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your tokens"
	@echo "2. Run 'make run' to start the bot"

check-env: ## Check if .env is configured
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@grep -q "your_bot_token_here" .env && echo "⚠️  TELEGRAM_BOT_TOKEN not configured!" || echo "✅ TELEGRAM_BOT_TOKEN configured"
	@grep -q "your_anthropic_api_key_here" .env && echo "⚠️  ANTHROPIC_API_KEY not configured!" || echo "✅ ANTHROPIC_API_KEY configured"
