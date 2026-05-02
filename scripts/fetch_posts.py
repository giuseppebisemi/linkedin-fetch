#!/usr/bin/env python3
"""
LinkedIn Company Posts Fetcher — Apify / HarvestAPI

Recupera i post di una pagina LinkedIn aziendale tramite l'actor
harvestapi/linkedin-company-posts su Apify, filtra per range di date
e salva un JSON.

Uso (usato dalla skill linkedin-fetch):
    python fetch_posts.py --company <slug|url> --from YYYY-MM-DD --to YYYY-MM-DD

Esempi:
    python fetch_posts.py --company nome-azienda --from 2026-04-01 --to 2026-04-30
    python fetch_posts.py --company https://www.linkedin.com/company/nome-azienda/ \
                            --from 2026-03-01 --to 2026-03-31
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from dotenv import load_dotenv
except ImportError as exc:
    missing = getattr(exc, "name", str(exc).split()[-1])
    print(f"Errore: dipendenza Python mancante ({missing}).")
    print("Esegui prima:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

load_dotenv(Path(__file__).parent / ".env")

APIFY_BASE      = "https://api.apify.com/v2"
ACTOR_ID        = "harvestapi~linkedin-company-posts"
ANTHROPIC_URL   = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

POLL_INTERVAL = 10   # secondi tra un poll e l'altro
POLL_TIMEOUT  = 300  # secondi massimi di attesa per il run


# ── API keys ──────────────────────────────────────────────────────────────────

def get_apify_token() -> str:
    key = os.environ.get("APIFY_API_TOKEN")
    if not key:
        print("Errore: APIFY_API_TOKEN non trovato.")
        print("")
        print("Per ottenerlo:")
        print("  1. Vai su https://console.apify.com/account/integrations")
        print("  2. Crea un nuovo token (o copia quello esistente)")
        print("  3. Esportalo come variabile d'ambiente:")
        print("       export APIFY_API_TOKEN='il_tuo_token'")
        print("     Oppure scrivilo nel file scripts/.env:")
        print("       APIFY_API_TOKEN=il_tuo_token")
        sys.exit(1)
    return key


def get_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Errore: ANTHROPIC_API_KEY non trovata. Necessaria solo per --dates.")
        print("Suggerimento: passa --from YYYY-MM-DD --to YYYY-MM-DD invece.")
        sys.exit(1)
    return key


# ── date helpers ──────────────────────────────────────────────────────────────

def parse_iso_date(s: str, *, end_of_day: bool = False) -> datetime:
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"Errore: data non valida '{s}'. Formato atteso: YYYY-MM-DD")
        sys.exit(1)
    return dt.replace(hour=23, minute=59, second=59) if end_of_day else dt


def parse_natural_dates(text: str) -> tuple[datetime, datetime]:
    """Fallback: chiede a Claude Haiku di interpretare un'espressione di date.
    Usato solo se l'utente passa --dates anziché --from/--to."""
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    prompt = (
        f"Oggi è {today}.\n"
        "L'utente ha scritto questa espressione di date: \"" + text + "\"\n\n"
        "Estrai la data di inizio e fine del range. "
        "Rispondi SOLO con un JSON nel formato: "
        "{\"from\": \"YYYY-MM-DD\", \"to\": \"YYYY-MM-DD\"}\n"
        "Nessun altro testo."
    )

    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": get_anthropic_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 64,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"Errore API Anthropic: {resp.status_code}")
        sys.exit(1)

    raw = resp.json()["content"][0]["text"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(raw)
        return (
            parse_iso_date(parsed["from"]),
            parse_iso_date(parsed["to"], end_of_day=True),
        )
    except Exception:
        print(f"Errore nel parsing delle date: {raw}")
        sys.exit(1)


# ── Apify ─────────────────────────────────────────────────────────────────────

def start_actor_run(company_url: str, date_from: datetime, token: str, max_posts: int = 0) -> tuple[str, str]:
    """Avvia il run dell'actor. Restituisce (run_id, dataset_id)."""
    resp = requests.post(
        f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
        params={"token": token},
        json={
            "targetUrls": [company_url],
            "postedLimitDate": date_from.strftime("%Y-%m-%d"),
            "maxPosts": max_posts,
        },
        timeout=30,
    )

    if resp.status_code == 401:
        print("Errore 401: APIFY_API_TOKEN non valido.")
        sys.exit(1)
    elif resp.status_code not in (200, 201):
        print(f"Errore Apify {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()["data"]
    return data["id"], data["defaultDatasetId"]


def wait_for_run(run_id: str, token: str, timeout: int = POLL_TIMEOUT) -> None:
    """Polling finché il run non termina."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            params={"token": token},
            timeout=15,
        )
        status = resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            return
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            print(f"\nErrore: run terminato con stato '{status}'.")
            print(f"Dettagli: https://console.apify.com/actors/runs/{run_id}")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(POLL_INTERVAL)

    print("\nTimeout: il run Apify non ha completato entro il tempo massimo.")
    sys.exit(1)


def fetch_dataset(dataset_id: str, token: str) -> list[dict]:
    """Scarica tutti gli item dal dataset Apify."""
    resp = requests.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={"token": token, "limit": 1000},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"Errore nel recupero del dataset: {resp.status_code}")
        sys.exit(1)
    return resp.json()


# ── filtering ─────────────────────────────────────────────────────────────────

def post_date(item: dict) -> datetime | None:
    """Estrae la data di pubblicazione da un item HarvestAPI."""
    date_str = (item.get("postedAt") or {}).get("date") or ""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def filter_posts(items: list[dict], date_from: datetime, date_to: datetime) -> list[dict]:
    result = []
    for item in items:
        dt = post_date(item)
        if dt and date_from <= dt <= date_to:
            result.append(item)
    return sorted(result, key=lambda item: (item.get("postedAt") or {}).get("date") or "")


# ── output ────────────────────────────────────────────────────────────────────

def save_json(posts: list[dict], slug: str) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path.cwd() / f"linkedin_posts_{slug}_{ts}.json"
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ── media download ────────────────────────────────────────────────────────────

def _ext_from_url(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix
    if ext:
        return ext
    lower = url.lower()
    if "mp4" in lower or "/vid/" in lower:
        return ".mp4"
    if "pdf" in lower:
        return ".pdf"
    if "image" in lower or "thumbnail" in lower or "cover" in lower:
        return ".jpg"
    return ".bin"


def _download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def download_media(posts: list[dict], slug: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    media_dir = Path.cwd() / f"linkedin_posts_{slug}_{ts}_media"
    media_dir.mkdir(parents=True, exist_ok=True)

    for post in posts:
        post_id = str(post.get("id", "unknown"))
        post_dir = media_dir / post_id
        post_dir.mkdir(exist_ok=True)

        images = post.get("postImages") or []
        if images:
            img_dir = post_dir / "images"
            img_dir.mkdir(exist_ok=True)
            for idx, url in enumerate(images, 1):
                ext = _ext_from_url(url) or ".jpg"
                _download_file(url, img_dir / f"image_{idx:03d}{ext}")

        video = post.get("postVideo") or {}
        video_url = video.get("videoUrl")
        thumb_url = video.get("thumbnailUrl")
        if video_url or thumb_url:
            vid_dir = post_dir / "video"
            vid_dir.mkdir(exist_ok=True)
            if thumb_url:
                ext = _ext_from_url(thumb_url) or ".jpg"
                _download_file(thumb_url, vid_dir / f"thumbnail{ext}")
            if video_url:
                ext = _ext_from_url(video_url) or ".mp4"
                _download_file(video_url, vid_dir / f"video{ext}")

        doc = post.get("document") or {}
        doc_url = doc.get("transcribedDocumentUrl")
        if doc_url:
            _download_file(doc_url, post_dir / "document.pdf")
        covers = doc.get("coverPages") or [] if doc else []
        if covers:
            cov_dir = post_dir / "covers"
            cov_dir.mkdir(exist_ok=True)
            for page_idx, page in enumerate(covers, 1):
                for img_idx, url in enumerate(page.get("imageUrls", []), 1):
                    ext = _ext_from_url(url) or ".jpg"
                    _download_file(url, cov_dir / f"cover_{page_idx:03d}_{img_idx:03d}{ext}")

    return media_dir


# ── main ──────────────────────────────────────────────────────────────────────

def resolve_company(raw: str) -> tuple[str, str]:
    """Normalizza l'input azienda in (company_url, slug)."""
    if raw.startswith("http"):
        url = raw if raw.endswith("/") else raw + "/"
        slug = raw.rstrip("/").split("/")[-1]
    else:
        slug = raw.strip("/")
        url = f"https://www.linkedin.com/company/{slug}/"
    return url, slug


def resolve_date_range(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.date_from and args.date_to:
        return (
            parse_iso_date(args.date_from),
            parse_iso_date(args.date_to, end_of_day=True),
        )
    if args.dates:
        print("AVVISO: --dates è deprecato e richiede ANTHROPIC_API_KEY.")
        print("         Converti le date in YYYY-MM-DD e usa --from / --to.")
        print("  Interpreto le date con Claude Haiku...", end=" ", flush=True)
        df, dt = parse_natural_dates(args.dates)
        print(f"{df.strftime('%d/%m/%Y')} → {dt.strftime('%d/%m/%Y')}")
        return df, dt
    print("Errore: specifica --from YYYY-MM-DD --to YYYY-MM-DD")
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(
        description="Recupera i post di una pagina LinkedIn aziendale tramite Apify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python fetch_posts.py --company nome-azienda --from 2026-04-01 --to 2026-04-30
  python fetch_posts.py --company https://www.linkedin.com/company/nome-azienda/ \\
                        --from 2026-03-01 --to 2026-03-31
        """,
    )
    parser.add_argument("--company", required=True, metavar="URL|SLUG",
                        help="URL LinkedIn o nome breve dell'azienda")
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD",
                        help="Data di inizio (inclusa). Usa con --to.")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD",
                        help="Data di fine (inclusa). Usa con --from.")
    parser.add_argument("--dates", metavar="TESTO",
                        help="DEPRECATO. Converti le date in YYYY-MM-DD e usa --from / --to.")
    parser.add_argument("--output", metavar="FILE",
                        help="File JSON di output (default: linkedin_posts_<slug>_<ts>.json nella CWD)")
    parser.add_argument("--max-posts", type=int, default=0, metavar="N",
                        help="Numero massimo di post da recuperare (default: 0 = tutti)")
    parser.add_argument("--timeout", type=int, default=POLL_TIMEOUT, metavar="SEC",
                        help="Timeout massimo di attesa per il run Apify (default: 300)")
    parser.add_argument("--download-media", action="store_true",
                        help="Scarica anche immagini, video e PDF allegati ai post")

    args = parser.parse_args()

    print("\n── LinkedIn Company Posts Fetcher ──")

    company_url, slug = resolve_company(args.company)
    date_from, date_to = resolve_date_range(args)

    token = get_apify_token()
    print(f"\nAvvio actor Apify per: {company_url}")
    run_id, dataset_id = start_actor_run(company_url, date_from, token, args.max_posts)
    print(f"Run ID: {run_id} — in attesa", end="", flush=True)
    wait_for_run(run_id, token, args.timeout)
    print(" completato.")

    print("Recupero dataset...", end=" ", flush=True)
    raw_items = fetch_dataset(dataset_id, token)
    print(f"{len(raw_items)} post recuperati dall'actor.")

    posts = filter_posts(raw_items, date_from, date_to)

    if not posts:
        print("\nNessun post trovato nel range di date specificato.")
        sys.exit(0)

    if args.output:
        path = Path(args.output)
        path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        path = save_json(posts, slug)
    print(f"\n{len(posts)} post salvati in: {path}")

    if args.download_media:
        media_dir = download_media(posts, slug)
        print(f"Contenuti multimediali salvati in: {media_dir}")


if __name__ == "__main__":
    main()
