# gdcruiser

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Install dependencies:
   ```bash
   uv sync
   ```

## Development

Run the CLI:
```bash
uv run gdcruiser
```

Run tests:
```bash
uv run pytest
```

Run linter:
```bash
uv run ruff check .
```

Format code:
```bash
uv run ruff format .
```
