# linkedin-fetch

Una skill per [Claude Code](https://claude.ai/code) che recupera i post da una pagina aziendale LinkedIn tramite [Apify](https://apify.com/) e li salva in formato JSON strutturato.

## Funzionalità

- Recupera i post dato l'URL o lo slug dell'azienda
- Filtra per intervallo di date o limita agli ultimi N post
- Timeout configurabile per l'esecuzione dello scraping su Apify
- Controllo automatico delle dipendenze e messaggi di errore chiari
- Output salvato come JSON con timestamp, testo completo e metriche di engagement

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

### Ultimi N post

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --from 2020-01-01 \
  --to 2026-05-03 \
  --max-posts 10
```

### Intervallo di date

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
| `--from YYYY-MM-DD` | Data inizio (inclusa) |
| `--to YYYY-MM-DD` | Data fine (inclusa) |
| `--max-posts N` | Numero massimo di post da recuperare (default: 0 = tutti) |
| `--timeout SEC` | Timeout di attesa per il run Apify in secondi (default: 300) |
| `--output FILE` | Percorso personalizzato per il file JSON di output |

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
| Dipendenza mancante | Esegui `pip install -r scripts/requirements.txt` |
| APIFY_API_TOKEN non trovato | Esporta il token o aggiungilo a `scripts/.env` |
| 401 da Apify | Verifica che il token sia valido e non scaduto |
| Timeout del run | Aumenta `--timeout` o controlla i log su console Apify |

## Licenza

MIT
