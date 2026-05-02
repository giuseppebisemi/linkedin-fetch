# linkedin-fetch

A [Claude Code](https://claude.ai/code) skill that fetches posts from a LinkedIn company page via [Apify](https://apify.com/) and saves them as structured JSON.

## Features

- Fetch posts by company URL or slug
- Filter by date range or limit to the latest N posts
- Configurable timeout for Apify scraping runs
- Automatic dependency checks and clear error messages
- Output saved as timestamped JSON with full post text and engagement metrics

## Prerequisites

- Python 3.8+
- An [Apify API token](https://console.apify.com/account/integrations)

## Installation

1. Clone or copy this skill into your Claude Code skills directory:
   ```bash
   git clone https://github.com/giuseppebisemi/linkedin-fetch.git
   ```

2. Install Python dependencies:
   ```bash
   pip install -r scripts/requirements.txt
   ```

3. Configure your Apify token:
   ```bash
   export APIFY_API_TOKEN="your_token_here"
   ```
   Or create a `scripts/.env` file:
   ```
   APIFY_API_TOKEN=your_token_here
   ```

## Usage

### Latest N posts

```bash
python3 scripts/fetch_posts.py \
  --company "lybra" \
  --from 2020-01-01 \
  --to 2026-05-03 \
  --max-posts 10
```

### Date range

```bash
python3 scripts/fetch_posts.py \
  --company "lybra" \
  --from 2026-04-01 \
  --to 2026-04-30
```

## Options

| Flag | Description |
|------|-------------|
| `--company URL\|SLUG` | LinkedIn company URL or slug (required) |
| `--from YYYY-MM-DD` | Start date (inclusive) |
| `--to YYYY-MM-DD` | End date (inclusive) |
| `--max-posts N` | Maximum posts to fetch (default: 0 = all) |
| `--timeout SEC` | Apify run timeout in seconds (default: 300) |
| `--output FILE` | Custom output JSON path |

## Project Structure

```
linkedin-fetch/
├── SKILL.md                  # Claude Code skill instructions
├── README.md                 # This file
├── .gitignore                # Excludes secrets and generated outputs
├── scripts/
│   ├── fetch_posts.py        # Main script
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variable template
└── references/
    └── apify-actor.md        # Apify actor API reference
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| Missing dependency | Run `pip install -r scripts/requirements.txt` |
| APIFY_API_TOKEN not found | Export the token or add it to `scripts/.env` |
| 401 from Apify | Check that your token is valid and not expired |
| Run timed out | Increase `--timeout` or check Apify console logs |

## License

MIT
