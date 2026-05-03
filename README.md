# linkedin-fetch

Una skill per [Claude Code](https://claude.ai/code) che recupera i post da una pagina aziendale LinkedIn tramite [Apify](https://apify.com/) e li salva in formato JSON strutturato.

## Funzionalità

- Recupera i post dato l'URL o lo slug dell'azienda
- Due modalità per la finestra temporale: range esplicito (`--from` / `--to`) o finestra relativa nativa dell'actor (`--posted-limit 24h|week|month|3months|6months|year|any`)
- Limita il numero massimo di post con `--max-posts`
- Timeout configurabile per l'esecuzione dello scraping su Apify
- Output JSON con item completo dell'actor: testo (`content`), autore, engagement (likes, commenti, shares, breakdown reazioni), URL canonico, media

## Prerequisiti

- Python 3.8+
- Un [token API Apify](https://console.apify.com/account/integrations)

## Installazione

1. Clona o copia questa skill nella tua directory di skill di Claude Code:
   ```bash
   git clone https://github.com/giuseppebisemi/linkedin-fetch.git
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

## Utilizzo

### Finestra relativa (più veloce)

Per "ultime 24h", "ultimo mese", "ultimo trimestre" ecc. usa `--posted-limit`. È mappato sul parametro nativo `postedLimit` dell'actor, che interrompe lo scroll quando esce dalla finestra.

```bash
python3 scripts/fetch_posts.py --company "nome-azienda" --posted-limit month
python3 scripts/fetch_posts.py --company "nome-azienda" --posted-limit 24h
```

### Ultimi N post

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --posted-limit any \
  --max-posts 10
```

### Intervallo di date specifico

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
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
│   ├── requirements.txt      # Dipendenze Python
│   └── .env.example          # Template delle variabili d'ambiente
└── references/
    └── apify-actor.md        # Riferimento API dell'actor Apify
```

## Risoluzione dei problemi

| Errore | Soluzione |
|--------|-----------|
| Dipendenza mancante (`apify-client`, `python-dotenv`) | Esegui `pip install -r scripts/requirements.txt` |
| APIFY_API_TOKEN non trovato | Esporta il token o aggiungilo a `scripts/.env` |
| 401 da Apify | Verifica che il token sia valido e non scaduto |
| Timeout del run | Aumenta `--timeout` o controlla i log su console Apify |

## Licenza

MIT
