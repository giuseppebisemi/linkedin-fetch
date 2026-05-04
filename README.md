# linkedin-fetch

Una skill per Claude Code che recupera post da pagine LinkedIn aziendali tramite Apify, con supporto per finestre temporali e download media.

## Funzionalità

- Recupera i post dato l'URL o lo slug dell'azienda
- Due modalità per la finestra temporale: range esplicito (`--from` / `--to`) o finestra relativa nativa dell'actor (`--posted-limit 24h|week|month|3months|6months|year|any`)
- Limita il numero massimo di post con `--max-posts`
- Timeout configurabile per l'esecuzione dello scraping su Apify
- Output JSON con item completo dell'actor: testo (`content`), autore, engagement (likes, commenti, shares, breakdown reazioni), URL canonico, media
- Scarica immagini, video e PDF allegati ai post (opzionale: usa `--download-media`)

## Prerequisiti

- Python 3.8+
- Un [token API Apify](https://console.apify.com/account/integrations)

## Installazione

1. Clona la skill nella directory `~/.claude/skills/` di Claude Code:
   ```bash
   git clone https://github.com/giuseppebisemi/linkedin-fetch.git ~/.claude/skills/linkedin-fetch
   ```

2. Installa le dipendenze Python:
   ```bash
   pip install -r scripts/requirements.txt
   ```

3. Configura il tuo token Apify:
   ```bash
   export APIFY_API_TOKEN="il_tuo_token"
   ```
   Oppure crea un file `scripts/.env`:
   ```
   APIFY_API_TOKEN=il_tuo_token
   ```

## Installazione veloce

Esegui lo script di setup per installare le dipendenze e configurare l'ambiente:

```bash
bash scripts/setup.sh
```

Questo script:
- Verifica Python 3.8+
- Installa le dipendenze da `requirements.txt`
- Crea il file `.env` da `.env.example`

## Verifica

Dopo l'installazione, esegui il test per verificare che tutto funzioni:

```bash
python3 scripts/test.py
```

## Utilizzo

### Invocazione naturale via `/linkedin-fetch` (modo consigliato)

Una volta installata in `~/.claude/skills/linkedin-fetch/`, la skill è disponibile in Claude Code come slash command. Lanciala scrivendo `/linkedin-fetch` seguito dalla richiesta in linguaggio naturale: Claude interpreta la richiesta, sceglie i flag corretti ed esegue lo script per te.

Claude estrae automaticamente:

- **L'azienda** — nome commerciale o URL LinkedIn. Se lo slug LinkedIn non coincide col nome (es. Anthropic → `anthropicresearch`), Claude esegue `scripts/search_company.py` (actor `harvestapi/linkedin-company-search`) e usa i risultati — `name`, `employeeCount`, `followerCount`, `locations`, `description` — per convergere allo slug giusto. Se ci sono più match, ti mostra le opzioni e chiede conferma prima del fetch.
- **La finestra temporale** — espressioni come "ultime 24h", "ultimo mese", "aprile 2026", "dal 1 al 15 marzo" vengono mappate sul flag corretto: `--posted-limit` per finestre relative native dell'actor (più veloce), `--from` / `--to` per range di calendario espliciti.
- **Modificatori** — frasi come "con i media", "con immagini", "scarica i video" aggiungono `--download-media`.

Esempi:

```
/linkedin-fetch ultimi 10 post di Anthropic
→ search_company.py risolve "anthropic" → "anthropicresearch"
→ python3 scripts/fetch_posts.py --company anthropicresearch --posted-limit any --max-posts 10

/linkedin-fetch post di LYBRA dell'ultimo mese
→ search_company.py ritorna 3 match (lybra-consulting, lybra-tech, lybra-destination)
→ Claude chiede quale; poi esegue fetch_posts.py --company <scelto> --posted-limit month

/linkedin-fetch post di Microsoft di aprile 2026 con immagini
→ python3 scripts/fetch_posts.py --company microsoft --from 2026-04-01 --to 2026-04-30 --download-media
```

La sezione successiva descrive l'invocazione diretta dello script Python (utile per scripting, automazioni, o quando si vuole bypassare l'interpretazione di Claude).

### Finestra relativa (più veloce)

Per "ultime 24h", "ultimo mese", "ultimo trimestre" ecc. usa `--posted-limit`. È mappato sul parametro nativo `postedLimit` dell'actor, che interrompe lo scroll quando esce dalla finestra.

```bash
python3 scripts/fetch_posts.py --company google --posted-limit month
python3 scripts/fetch_posts.py --company google --posted-limit 24h
```

### Ultimi N post

```bash
python3 scripts/fetch_posts.py \
  --company google \
  --posted-limit any \
  --max-posts 10
```

### Intervallo di date specifico

```bash
python3 scripts/fetch_posts.py \
  --company google \
  --from 2026-04-01 \
  --to 2026-04-30
```

## Opzioni

| Flag | Descrizione |
|------|-------------|
| `--company URL\|SLUG` | URL o slug della pagina LinkedIn (obbligatorio) |
| `--posted-limit WINDOW` | Finestra relativa: `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year`, `any`. Mutuamente esclusivo con `--from`/`--to`. |
| `--from YYYY-MM-DD` | Data inizio (inclusa) |
| `--to YYYY-MM-DD` | Data fine (inclusa) |
| `--max-posts N` | Numero massimo di post da recuperare (default: 0 = tutti) |
| `--timeout SEC` | Timeout di attesa per il run Apify in secondi (default: 300) |
| `--output FILE` | Percorso personalizzato per il file JSON di output |
| `--download-media` | Scarica anche immagini, video e PDF allegati ai post |

## Struttura del progetto

```
linkedin-fetch/
├── SKILL.md                  # Istruzioni della skill per Claude Code
├── README.md                 # Questo file
├── .gitignore                # Esclude secret e output generati
├── scripts/
│   ├── fetch_posts.py        # Script principale
│   ├── setup.sh              # Script di installazione dipendenze
│   ├── test.py               # Smoke test script
│   ├── requirements.txt      # Dipendenze Python
│   ├── .env                  # Token Apify (non tracciato da git)
│   └── .env.example          # Template delle variabili d'ambiente
└── references/
    └── apify-actor.md        # Riferimento API dell'actor Apify
```

## Risoluzione dei problemi

| Errore | Soluzione |
|--------|-----------|
| Dipendenza mancante (`apify-client`, `python-dotenv`) | Esegui `bash scripts/setup.sh` |
| APIFY_API_TOKEN non trovato | Usa `bash scripts/setup.sh` e compila `.env`, oppure esporta il token |
| 401 da Apify | Verifica che il token sia valido e non scaduto |
| Timeout del run | Aumenta `--timeout` o controlla i log su console Apify |
| Errore: specifica --from...oppure --posted-limit | Usa `--posted-limit any` se vuoi tutti i post o specifica un range con `--from`/`--to` |

## Licenza

MIT
