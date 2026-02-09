# SQL agent analysis system

## Overview

This is an SQL agent which enables a user to query a database (based on parsed emails).

## Setup

Set the keys in `.env`

### Docker

```bash
docker-compose up --build
```

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
