#!/usr/bin/env python3
"""
LinkedIn Company Posts Fetcher — Apify / HarvestAPI

Recupera i post di una pagina LinkedIn aziendale tramite l'actor
harvestapi/linkedin-company-posts su Apify e salva un JSON.

Due modalità per limitare la finestra temporale:
- --from / --to     range esplicito (lower bound passato all'actor come
                    `postedLimitDate`, upper bound applicato lato script)
- --posted-limit    finestra relativa nativa dell'actor: 24h, week, month,
                    3months, 6months, year, any. Più efficiente di --from
                    quando vuoi "ultime 24h / ultimo mese" perché l'actor
                    interrompe lo scroll non appena esce dalla finestra.

Esempi:
    python fetch_posts.py --company nome-azienda --from 2026-04-01 --to 2026-04-30
    python fetch_posts.py --company nome-azienda --posted-limit month --max-posts 50
    python fetch_posts.py --company nome-azienda --posted-limit 24h
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

try:
    from apify_client import ApifyClient
    from apify_client.errors import ApifyApiError
    from dotenv import load_dotenv
except ImportError as exc:
    missing = getattr(exc, "name", str(exc).split()[-1])
    print(f"Errore: dipendenza Python mancante ({missing}).")
    print("Esegui prima:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

load_dotenv(Path(__file__).parent / ".env")

ACTOR_ID = "harvestapi~linkedin-company-posts"

POSTED_LIMIT_CHOICES = ("1h", "24h", "week", "month", "3months", "6months", "year", "any")


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


# ── date helpers ──────────────────────────────────────────────────────────────

def parse_iso_date(s: str, *, end_of_day: bool = False) -> datetime:
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"Errore: data non valida '{s}'. Formato atteso: YYYY-MM-DD")
        sys.exit(1)
    return dt.replace(hour=23, minute=59, second=59) if end_of_day else dt


# ── Apify ─────────────────────────────────────────────────────────────────────

def run_actor(
    client: ApifyClient,
    company_url: str,
    *,
    date_from: datetime | None = None,
    posted_limit: str | None = None,
    max_posts: int = 0,
    timeout: int = 300,
) -> tuple[str, str]:
    """Avvia il run e attende il completamento. Restituisce (run_id, dataset_id)."""
    body: dict = {"targetUrls": [company_url], "maxPosts": max_posts}
    if date_from is not None:
        body["postedLimitDate"] = date_from.strftime("%Y-%m-%d")
    if posted_limit is not None:
        body["postedLimit"] = posted_limit

    run = client.actor(ACTOR_ID).call(run_input=body, timeout_secs=timeout)

    if run["status"] != "SUCCEEDED":
        print(f"\nErrore: run terminato con stato '{run['status']}'.")
        print(f"Dettagli: https://console.apify.com/actors/runs/{run['id']}")
        sys.exit(1)

    return run["id"], run["defaultDatasetId"]


def fetch_dataset(client: ApifyClient, dataset_id: str) -> list[dict]:
    """Scarica tutti gli item dal dataset, paginando automaticamente."""
    return list(client.dataset(dataset_id).iterate_items())


# ── filtering ─────────────────────────────────────────────────────────────────

def post_date(item: dict) -> datetime | None:
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


def sort_by_date(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: (item.get("postedAt") or {}).get("date") or "")


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
        with urlopen(url, timeout=60) as resp:
            if resp.status == 200:
                dest.write_bytes(resp.read())
                return True
    except (URLError, HTTPError, TimeoutError):
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
        else:
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


def main():
    parser = argparse.ArgumentParser(
        description="Recupera i post di una pagina LinkedIn aziendale tramite Apify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python fetch_posts.py --company nome-azienda --from 2026-04-01 --to 2026-04-30
  python fetch_posts.py --company nome-azienda --posted-limit month --max-posts 50
  python fetch_posts.py --company nome-azienda --posted-limit 24h
        """,
    )
    parser.add_argument("--company", required=True, metavar="URL|SLUG",
                        help="URL LinkedIn o nome breve dell'azienda")
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD",
                        help="Data di inizio (inclusa). Usa con --to. Mutuamente esclusivo con --posted-limit.")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD",
                        help="Data di fine (inclusa). Usa con --from.")
    parser.add_argument("--posted-limit", choices=POSTED_LIMIT_CHOICES, metavar="WINDOW",
                        help="Finestra temporale relativa nativa dell'actor: "
                             + ", ".join(POSTED_LIMIT_CHOICES)
                             + ". Più efficiente di --from/--to per richieste tipo 'ultime 24h' o 'ultimo mese'.")
    parser.add_argument("--output", metavar="FILE",
                        help="File JSON di output (default: linkedin_posts_<slug>_<ts>.json nella CWD)")
    parser.add_argument("--max-posts", type=int, default=0, metavar="N",
                        help="Numero massimo di post da recuperare (default: 0 = tutti)")
    parser.add_argument("--timeout", type=int, default=300, metavar="SEC",
                        help="Timeout massimo di attesa per il run Apify (default: 300)")
    parser.add_argument("--download-media", action="store_true",
                        help="Scarica anche immagini, video e PDF allegati ai post")

    args = parser.parse_args()

    # Validazione modalità: o range esplicito o finestra relativa, non entrambi.
    has_range = bool(args.date_from or args.date_to)
    has_limit = bool(args.posted_limit)
    if has_range and has_limit:
        print("Errore: --from/--to e --posted-limit sono mutuamente esclusivi.")
        sys.exit(2)
    if not has_range and not has_limit:
        print("Errore: specifica --from YYYY-MM-DD --to YYYY-MM-DD oppure --posted-limit WINDOW.")
        sys.exit(2)
    if has_range and not (args.date_from and args.date_to):
        print("Errore: --from e --to vanno usati insieme.")
        sys.exit(2)

    date_from = parse_iso_date(args.date_from) if args.date_from else None
    date_to   = parse_iso_date(args.date_to, end_of_day=True) if args.date_to else None

    print("\n── LinkedIn Company Posts Fetcher ──")

    company_url, slug = resolve_company(args.company)
    token = get_apify_token()
    client = ApifyClient(token)

    print(f"\nAvvio actor Apify per: {company_url}")
    if args.posted_limit:
        print(f"Finestra: postedLimit={args.posted_limit}")
    else:
        print(f"Finestra: {args.date_from} → {args.date_to}")
    print("Run avviato, in attesa del completamento (può richiedere alcuni minuti)...")

    try:
        run_id, dataset_id = run_actor(
            client,
            company_url,
            date_from=date_from,
            posted_limit=args.posted_limit,
            max_posts=args.max_posts,
            timeout=args.timeout,
        )
    except ApifyApiError as e:
        if e.status_code == 401:
            print("Errore 401: APIFY_API_TOKEN non valido.")
        else:
            print(f"Errore Apify {e.status_code}: {e}")
        sys.exit(1)

    print(f"Run completato (ID: {run_id}).")

    print("Recupero dataset...", end=" ", flush=True)
    raw_items = fetch_dataset(client, dataset_id)
    print(f"{len(raw_items)} post recuperati dall'actor.")

    if date_from and date_to:
        posts = filter_posts(raw_items, date_from, date_to)
    else:
        posts = sort_by_date(raw_items)

    if not posts:
        print("\nNessun post trovato.")
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
