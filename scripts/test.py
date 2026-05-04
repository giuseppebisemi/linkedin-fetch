#!/usr/bin/env python3
"""
LinkedIn Fetch — Smoke Test

Esegue un test veloce dello script verificando:
- Lo script esiste ed è eseguibile
- Le dipendenze sono installate
- L'actor Apify viene chiamato con successo
- L'output JSON è valido e contiene campi essenziali

Usage:
    python3 test.py [--company SLUG] [--max-posts N] [--quiet]

Options:
    --company SLUG   Azienda di test (default: anthropicresearch)
    --max-posts N    Numero di post da recuperare (default: 2)
    --quiet          Non stampare output dettagliato
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd: list[str], cwd: Path, quiet: bool = False) -> tuple[bool, str, str]:
    """Esegue un comando shell e restituisce (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout raggiunto"
    except Exception as e:
        return False, "", str(e)


def main():
    parser = argparse.ArgumentParser(description="Smoke test per linkedin-fetch")
    parser.add_argument("--company", default="anthropicresearch", help="Slug azienda di test")
    parser.add_argument("--max-posts", type=int, default=2, help="Post da recuperare")
    parser.add_argument("--quiet", action="store_true", help="Output minimale")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    success = True

    # ── 1. Verifica Python ───────────────────────────────────────────────────
    if not args.quiet:
        print("\n── Step 1/5: Verifica Python ──")

    try:
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("❌ Python non funzionante")
            success = False
        else:
            version = result.stdout.strip() or result.stderr.strip()
            if not args.quiet:
                print(f"✅ {version}")
    except Exception as e:
        print(f"❌ Errore Python: {e}")
        success = False

    # ── 2. Verifica dipendenze ───────────────────────────────────────────────
    if not args.quiet:
        print("\n── Step 2/5: Verifica dipendenze ──")

    try:
        # Controlla apify-client
        result = subprocess.run(
            [sys.executable, "-c", "import apify_client"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("❌ apify-client non installato")
            success = False
        else:
            if not args.quiet:
                print("✅ apify-client installato")

        # Controlla python-dotenv
        result = subprocess.run(
            [sys.executable, "-c", "from dotenv import load_dotenv"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("❌ python-dotenv non installato")
            success = False
        else:
            if not args.quiet:
                print("✅ python-dotenv installato")
    except Exception as e:
        print(f"❌ Errore verifica dipendenze: {e}")
        success = False

    # ── 3. Verifica script esiste ────────────────────────────────────────────
    if not args.quiet:
        print("\n── Step 3/5: Verifica script ──")

    fetch_script = script_dir / "fetch_posts.py"
    if not fetch_script.exists():
        print(f"❌ Script non trovato: {fetch_script}")
        success = False
    else:
        if not args.quiet:
            print(f"✅ Script trovato: {fetch_script}")

    # ── 4. Verifica token APIFY ──────────────────────────────────────────────
    if not args.quiet:
        print("\n── Step 4/5: Verifica APIFY_API_TOKEN ──")

    token = os.environ.get("APIFY_API_TOKEN")
    env_file = script_dir / ".env"

    if not token:
        if env_file.exists():
            # Prova a caricare da .env
            load_env_success = False
            try:
                # Carica manualmente (senza import dotenv per evitare errori)
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("APIFY_API_TOKEN="):
                            token = line.split("=", 1)[1].strip("'\"")
                            load_env_success = True
                            break
            except Exception:
                pass

            if not load_env_success:
                print("❌ APIFY_API_TOKEN non configurato in .env")
                success = False
            elif not token:
                print("❌ APIFY_API_TOKEN vuoto in .env")
                success = False
            else:
                if not args.quiet:
                    print("✅ Token trovato in .env (inizializzato)")
        else:
            print("❌ APIFY_API_TOKEN non configurato")
            print("   Esegui: bash scripts/setup.sh")
            success = False
    else:
        if not args.quiet:
            print("✅ APIFY_API_TOKEN trovato in ambiente")

    # ── 5. Test run (se possibile) ───────────────────────────────────────────
    if not args.quiet:
        print("\n── Step 5/5: Test run ──")

    if not success:
        print("❌ Saltato: verifiche precedenti fallite")
    elif not token:
        print("❌ Saltato: token non configurato")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            cmd = [
                sys.executable,
                str(fetch_script),
                "--company", args.company,
                "--posted-limit", "any",
                "--max-posts", str(args.max_posts),
                "--output", str(tmpdir_path / "output"),
                "--download-media"
            ]

            if not args.quiet:
                print(f"Comando: {' '.join(cmd)}")
                print("Esecuzione in corso (può richiedere 30-60 secondi)...")

            run_success, stdout, stderr = run_command(cmd, script_dir, quiet=True)

            if not run_success:
                print("❌ Run fallito")
                if stderr:
                    print(f"   stderr: {stderr[:500]}")
                success = False
            else:
                # Verifica output
                json_files = list(tmpdir_path.glob("**/*.json"))
                media_dirs = list(tmpdir_path.glob("**/media/"))

                if not json_files:
                    print("❌ Nessun file JSON generato")
                    success = False
                else:
                    json_path = json_files[0]
                    try:
                        with open(json_path) as f:
                            data = json.load(f)

                        if not isinstance(data, list):
                            print("❌ JSON non è un array")
                            success = False
                        elif len(data) == 0:
                            print("⚠️  JSON vuoto (azienda senza post)")
                            # Non consideriamo un errore fatale
                        elif len(data) < args.max_posts:
                            print(f"⚠️  Solo {len(data)} post recuperati (richiesti {args.max_posts})")
                        else:
                            # Verifica campi essenziali
                            post = data[0]
                            essential_fields = ["id", "content", "author", "engagement"]
                            missing = [f for f in essential_fields if f not in post]
                            if missing:
                                print(f"❌ Campi mancanti nel JSON: {missing}")
                                success = False
                            else:
                                if not args.quiet:
                                    print(f"✅ {len(data)} post recuperati")
                                    print("✅ Campi essenziali presenti: id, content, author, engagement")
                                    if media_dirs:
                                        media_files = list(media_dirs[0].rglob("*"))
                                        print(f"✅ Media scaricati ({len([f for f in media_files if f.is_file()])} file)")
                                    else:
                                        print("ℹ️  Nessun media scaricato (nessun post con immagini/video)")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON non valido: {e}")
                        success = False
                    except Exception as e:
                        print(f"❌ Errore lettura JSON: {e}")
                        success = False

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 40)
    if success:
        print("✅ TEST PASSATO")
        return 0
    else:
        print("❌ TEST FALLITO")
        return 1


if __name__ == "__main__":
    sys.exit(main())
