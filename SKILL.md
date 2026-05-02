---
name: linkedin-fetch
description: Recupera e salva in JSON i post di una pagina LinkedIn aziendale tramite Apify. Usa questa skill ogni volta che l'utente vuole scaricare post LinkedIn, recuperare post da una company page, creare un report di post LinkedIn, o fare scraping di una pagina aziendale su LinkedIn — anche se non usa esplicitamente la parola "skill". Triggera per frasi come "scarica i post di", "recupera i post LinkedIn di", "fetch LinkedIn", "voglio i post di [azienda] su LinkedIn", "prendi i post di aprile", ecc.
---

Questa skill orchestra `fetch_posts.py` per recuperare post da una pagina LinkedIn aziendale tramite Apify e salvarli in un file JSON locale.

## Prerequisiti

Prima di eseguire lo script, verifica che l'ambiente sia pronto:

1. **Dipendenze Python** — Lo script richiede `requests` e `python-dotenv`. Se mancano, installale:
   ```bash
   pip install -r scripts/requirements.txt
   ```
   Lo script stesso ora controlla le dipendenze all'avvio e guida l'utente se mancano.

2. **Token Apify** — Lo script legge `APIFY_API_TOKEN` dal file `scripts/.env` o dalle variabili d'ambiente.
   Se il token manca, lo script stampa istruzioni dettagliate su come ottenerlo su https://console.apify.com/account/integrations.

Se durante l'esecuzione compare "Errore: APIFY_API_TOKEN non trovato", guida l'utente a configurarlo prima di riprovare.

## Flusso in 3 passi

### 1. Raccogli i parametri dall'utente

Prima di eseguire qualsiasi comando, chiedi (se non già forniti nel messaggio):

- **URL** della pagina LinkedIn (es. `https://www.linkedin.com/company/lybra/` oppure solo lo slug `lybra`)
- **Modalità**:
  - *Ultimi N post* — chiedi quanti (default: 10)
  - *Range di date* — chiedi l'espressione in linguaggio naturale (es. `"aprile 2026"`, `"dal 1 marzo al 30 marzo 2026"`). Convertila in date `YYYY-MM-DD` esplicite.

Se l'utente fornisce già URL e parametri nel messaggio originale, salta le domande e procedi direttamente.

**Pattern URL → slug:** Se l'utente passa un URL completo come `https://www.linkedin.com/company/lybra/`, estrai lo slug (`lybra`) e passalo a `--company`. Lo script accetta sia URL che slug, ma passare lo slug nel `--company` è sufficiente.

### 2. Esegui lo script

Lo script usa `argparse`. I percorsi sono:

```
PYTHON = python3
SCRIPT = scripts/fetch_posts.py
```

**Modalità ultimi N post:**

Usa `--max-posts N` con un range di date molto ampio (dal 2020-01-01 a oggi):

```bash
python3 scripts/fetch_posts.py \
  --company "lybra" \
  --from 2020-01-01 \
  --to $(date +%Y-%m-%d) \
  --max-posts 10
```

**Modalità range di date:**

Converti l'espressione in date esplicite `YYYY-MM-DD` e passale con `--from` / `--to`:

```bash
python3 scripts/fetch_posts.py \
  --company "lybra" \
  --from 2026-04-01 \
  --to 2026-04-30
```

Parametri principali dello script:
| Flag | Descrizione |
|------|-------------|
| `--company URL\|SLUG` | URL LinkedIn o slug dell'azienda (obbligatorio) |
| `--from YYYY-MM-DD` | Data inizio range (inclusa) |
| `--to YYYY-MM-DD` | Data fine range (inclusa) |
| `--max-posts N` | Numero massimo di post da recuperare (default: 0 = tutti) |
| `--output FILE` | File JSON di output personalizzato |
| `--timeout SEC` | Timeout massimo di attesa per il run Apify (default: 300 secondi) |

**Nota sul tempo di esecuzione:** Il run Apify può richiedere da 30 secondi a diversi minuti. Durante l'attesa, lo script stampa un punto ogni 10 secondi. Informa l'utente che stai aspettando, soprattutto se il run sembra bloccarsi.

### 3. Mostra il risultato

Dopo l'esecuzione, riporta all'utente:
- Il **path completo del file JSON** prodotto (visibile nell'output dopo "post salvati in:")
- Il **numero di post trovati**
- Eventuali errori (token Apify non valido, URL non trovato, ecc.)

## Gestione degli errori

| Scenario | Causa | Azione |
|----------|-------|--------|
| Errore: dipendenza Python mancante | `requests` o `python-dotenv` non installati | Esegui `pip install -r requirements.txt` |
| Errore: APIFY_API_TOKEN non trovato | Token non configurato | Guida l'utente a crearlo su https://console.apify.com/account/integrations e a scriverlo in `scripts/.env` |
| Errore 401 Apify | `APIFY_API_TOKEN` non valido | Verifica che il token sia corretto e non scaduto |
| RUN FAILED / TIMED-OUT | Apify non è riuscito a completare lo scraping | Controlla i log su `https://console.apify.com/actors/runs/<run_id>` |
| URL non trovato | Slug azienda errato | Verifica il nome nell'URL LinkedIn |
| Nessun post trovato | Range di date senza post | Allarga il range o controlla che la pagina sia attiva |

## Esempio di interazione completa

**Utente:** "Scarica gli ultimi 10 post di Lybra da LinkedIn"

**Modello:** (non chiede nulla, parametri già forniti)

**Modello:** "Avvio lo script... (il run Apify può richiedere qualche minuto)"

```bash
python3 scripts/fetch_posts.py \
  --company "lybra" \
  --from 2020-01-01 \
  --to 2026-05-02 \
  --max-posts 10
```

**Modello:** "10 post salvati in: `/percorso/linkedin_posts_lybra_20260502_143022.json`"

## Riferimenti tecnici

Per i dettagli sui parametri dell'actor Apify, la struttura del dataset e la mappatura degli endpoint REST, consulta `references/apify-actor.md`.
