# ELDORADO OFFER PLACER

Small Python bot for automating offer placing to Eldorado.

## Features
- Configurable connectors for web/API access
- Background job loop and simple scheduler
- Pluggable notification backends (email, webhook, Telegram)
- Basic logging and error handling

## Requirements
- Python 3.11
- pip

Recommended: use a virtual environment.

## Installation
Clone the repository and install dependencies:

```bash
git clone <repo-url> bot_eldorado
cd bot_eldorado
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration
Configure via environment variables or a `.env` file (example):

```env
ELDORADO_API_URL=https://api.eldorado.example
ELDORADO_API_KEY=your_api_key_here
NOTIFY_WEBHOOK=https://hooks.example/service
LOG_LEVEL=INFO
```

Load `.env` in startup or use python-dotenv.

## Usage
Run the bot entry point:

```bash
python -m bot_eldorado.main
```

Common commands (project-specific):

```bash
# start in foreground
python -m bot_eldorado.main

# run a single task
python -m bot_eldorado.tasks.check_availability --item-id 12345
```

Adjust commands to match available modules in the repository.

## Development
- Follow black for formatting and ruff/flake8 for linting.
- Add new features behind feature flags or config.
- Keep functions small and testable.

Example tooling:

```bash
pip install -r dev-requirements.txt
black .
ruff .
```

## Testing
Use pytest:

```bash
pytest tests
```

Include unit tests for scraping, API clients, and notification flows. Mock external calls.

## Docker (optional)
Simple Dockerfile pattern:

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "-m", "bot_eldorado.main"]
```

## Contributing
- Open issues for bugs and feature requests.
- Create small, focused PRs with tests.
- Follow repository code style and add documentation for new behavior.
