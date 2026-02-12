# SQL agent analysis system

## Overview

This is an SQL agent which enables a user to query a database (based on parsed emails).

## Setup

Set the keys in `.env`

### Docker

```bash
docker-compose up --build
```

### Seed Mock Data

Populate the database with realistic mock data for local development:

```bash
# Using docker-compose (recommended)
# First, ensure a clean state:
docker-compose down --remove-orphans

# Run the seed profile (starts db dependency automatically)
docker-compose --profile seed up seed --build

# After seeding completes, bring down the seed profile
docker-compose --profile seed down --remove-orphans
```

**Troubleshooting**: If you see "network not found" errors, run:

```bash
docker-compose down --volumes --remove-orphans && docker system prune -f
```

```bash
# Or manually with uv (requires local PostgreSQL)
cd backend
uv run python -m workflow.database.seed.seed_database --count 1000 --reset
```

Options:

- `--count N`: Number of inventory items to create (default: 1000)
- `--reset`: Drop and recreate tables before seeding
- `--dry-run`: Preview what would be created without writing
- `--seed N`: Random seed for reproducible data
- `--categories`: Comma-separated list (e.g., `fasteners,gaskets`)

See [backend/workflow/database/seed/README.md](backend/workflow/database/seed/README.md) for details.

### Debug/Develop

```bash
# Get the database and redis caching set up
docker-compose up pgdb redis
```

```bash
# Install and run the frontend
cd frontend
npm i
```

```bash
# Install and run the backend (assumes you have uv installed)
cd backend_agent
uv sync
```

If using a VSCode like product, the `.vscode/launch.json` is already setup to debug using the `Full-stack` configuration.

### Perform load testing

See [load testing](backend/loadtests/README.md) for details.

## Product Configuration

This is the key product of this project. Effectively the way that a construction company would identify/structure/prioritize the details of their products is encoded in this way.

Example `config/products_config.yaml`:

```yaml
products:
  - name: 'Fasteners'
    category: 'Fasteners'
    aliases: ['bolts', 'nuts', 'screws', 'washers']
    properties:
      - name: 'grade'
        type: 'string'
        examples: ['2', '5', '8', 'A490']
      - name: 'size'
        type: 'string'
        examples: ['1/2-13', '3/4-10', 'M12']
      - name: 'length'
        type: 'string'
        examples: ['2"', '3 inches', '50mm']
      - name: 'finish'
        type: 'string'
        examples: ['zinc plated', 'galvanized', 'plain']
      - name: 'material'
        type: 'string'
        examples: ['steel', 'stainless', 'brass']

  - name: 'Threaded Rod'
    category: 'Threaded Rod'
    aliases: ['all-thread', 'threaded bar']
    properties:
      - name: 'diameter'
        type: 'string'
      - name: 'length'
        type: 'string'
      - name: 'grade'
        type: 'string'

extraction_rules:
  quantity_patterns:
    - "\\d+\\s*pcs?"
    - "\\d+\\s*pieces?"
    - "\\d+\\s*units?"
  date_formats:
    - '%m/%d/%Y'
    - '%d-%m-%Y'
    - '%B %d, %Y'
```
