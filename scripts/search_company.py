#!/usr/bin/env python3
"""
LinkedIn Company Search — Risolve il nome commerciale di un'azienda nello slug LinkedIn.

Chiama l'actor harvestapi/linkedin-company-search su Apify e restituisce
i risultati con i campi necessari per disambiguare.

Uso:
    python3 search_company.py --query "LYBRA"
    python3 search_company.py --query "Siemens" --max-results 5
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from apify_client import ApifyClient
    from apify_client.errors import ApifyApiError
    from dotenv import load_dotenv
except ImportError as exc:
    missing = getattr(exc, "name", str(exc).split()[-1])
    print(f"Errore: dipendenza Python mancante ({missing}).", file=sys.stderr)
    print("Esegui: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

load_dotenv(Path(__file__).parent / ".env")

SEARCH_ACTOR_ID = "harvestapi~linkedin-company-search"


def get_token() -> str:
    key = os.environ.get("APIFY_API_TOKEN")
    if not key:
        print("Errore: APIFY_API_TOKEN non trovato.", file=sys.stderr)
        sys.exit(1)
    return key


def search_companies(client: ApifyClient, query: str, max_items: int = 10) -> list[dict]:
    """Cerca aziende su LinkedIn e restituisce i risultati."""
    run_input = {
        "searchQuery": query,
        "scraperMode": "full",
        "maxItems": max_items,
    }

    run = client.actor(SEARCH_ACTOR_ID).call(run_input=run_input, timeout_secs=120)

    if run["status"] != "SUCCEEDED":
        print(f"Errore: search run terminato con stato '{run['status']}'.", file=sys.stderr)
        sys.exit(1)

    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return raw


def extract_fields(companies: list[dict]) -> list[dict]:
    """Estrae solo i campi utili per la disambiguazione, ordinati per followerCount."""
    results = []
    for c in companies:
        locations = c.get("locations") or []
        locs = [{"city": loc.get("city"), "country": (loc.get("parsed") or {}).get("country") or loc.get("country")}
                for loc in locations if loc.get("city") or loc.get("country")]

        results.append({
            "universalName": c.get("universalName", ""),
            "name": c.get("name", ""),
            "linkedinUrl": c.get("linkedinUrl", ""),
            "employeeCount": c.get("employeeCount"),
            "followerCount": c.get("followerCount"),
            "description": c.get("description", ""),
            "locations": locs,
        })

    results.sort(key=lambda r: r.get("followerCount") or 0, reverse=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Cerca aziende su LinkedIn e restituisce lo slug (universalName)."
    )
    parser.add_argument("--query", required=True, metavar="NAME",
                        help="Nome dell'azienda da cercare (es. 'LYBRA', 'Anthropic')")
    parser.add_argument("--max-results", type=int, default=10, metavar="N",
                        help="Numero massimo di risultati (default: 10)")
    args = parser.parse_args()

    token = get_token()
    client = ApifyClient(token)

    print(f"Cercando '{args.query}' su LinkedIn...", file=sys.stderr)

    try:
        companies = search_companies(client, args.query, args.max_results)
    except ApifyApiError as e:
        if e.status_code == 401:
            print("Errore 401: APIFY_API_TOKEN non valido.", file=sys.stderr)
        else:
            print(f"Errore Apify {e.status_code}: {e}", file=sys.stderr)
        sys.exit(1)

    results = extract_fields(companies)

    if not results:
        print(f"Nessuna azienda trovata per '{args.query}'.", file=sys.stderr)
        sys.exit(0)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
