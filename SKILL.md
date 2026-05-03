---
name: linkedin-fetch
description: Scarica i post di una pagina LinkedIn aziendale via Apify e li salva in JSON. Usa questa skill ogni volta che l'utente vuole recuperare, scaricare, esportare o fare scraping di post da una company page LinkedIn, anche se non nomina la skill. Triggera su frasi tipo "scarica i post di [azienda]", "recupera i post LinkedIn di X", "fetch LinkedIn", "voglio gli ultimi N post di [azienda]", "post di [azienda] di aprile/marzo/ultimo trimestre", "esporta i post LinkedIn di X".
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

- **URL** della pagina LinkedIn (es. `https://www.linkedin.com/company/nome-azienda/` oppure solo lo slug `nome-azienda`)
- **Quale finestra temporale**: ultimi N post, ultime 24h/settimana/mese, oppure un range di date specifico.

Se l'utente fornisce già URL e parametri nel messaggio originale, salta le domande e procedi direttamente.

**Pattern URL → slug:** Se l'utente passa un URL completo come `https://www.linkedin.com/company/nome-azienda/`, estrai lo slug (`nome-azienda`) e passalo a `--company`. Lo script accetta sia URL che slug, ma passare lo slug è più pulito.

### 2. Esegui lo script

Lo script ha due modalità mutuamente esclusive per la finestra temporale: `--posted-limit` (finestra relativa nativa dell'actor) oppure `--from`/`--to` (range esplicito). **Scegli sempre la modalità più efficiente in base alla richiesta dell'utente.**

#### Quando usare `--posted-limit` (preferita per richieste relative)

`--posted-limit` mappa il parametro `postedLimit` dell'actor HarvestAPI: l'actor stesso interrompe lo scroll del feed quando esce dalla finestra. È **molto più veloce** di `--from`/`--to` per richieste tipo "ultime 24h" o "ultimo mese", perché evita download e filtri lato client.

Valori accettati: `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year`, `any`.

| Richiesta utente | Modalità da usare |
|------------------|-------------------|
| "ultime 24 ore", "oggi", "ieri" | `--posted-limit 24h` |
| "questa settimana", "ultimi 7 giorni" | `--posted-limit week` |
| "ultimo mese", "ultimi 30 giorni" | `--posted-limit month` |
| "ultimo trimestre" | `--posted-limit 3months` |
| "ultimo semestre" | `--posted-limit 6months` |
| "ultimo anno" | `--posted-limit year` |
| "tutti i post" | `--posted-limit any` (combina con `--max-posts` se vuoi un limite) |

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --posted-limit month
```

Per "ultimi N post" combina `--posted-limit any` con `--max-posts N`:

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --posted-limit any \
  --max-posts 10
```

#### Quando usare `--from` / `--to` (range esplicito)

Usa `--from` / `--to` solo quando l'utente specifica un **mese o intervallo specifico nel calendario** (es. "aprile 2026", "dal 1 marzo al 15 marzo 2026"). Converti l'espressione in date `YYYY-MM-DD` esplicite (oggi è la data nel system prompt; basa i calcoli su quella).

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --from 2026-04-01 \
  --to 2026-04-30
```

**Importante — limite dell'actor:** Il parametro `postedLimitDate` esposto dall'actor è solo un limite **inferiore**. Quando passi `--from 2024-03-01 --to 2024-03-31`, l'actor scrolla dal post più recente fino al 1 marzo 2024 fetchando *tutti* i post intermedi, e lo script poi filtra `--to` lato client. Più `--from` è lontana nel passato, più lungo è il run. Per range stretti in epoche lontane avvisa l'utente e valuta di alzare `--timeout` oltre i 300 secondi di default.

#### Tabella flag

| Flag | Descrizione |
|------|-------------|
| `--company URL\|SLUG` | URL LinkedIn o slug dell'azienda (obbligatorio) |
| `--posted-limit WINDOW` | Finestra relativa: `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year`, `any`. Mutuamente esclusivo con `--from`/`--to`. |
| `--from YYYY-MM-DD` | Data inizio range (inclusa). Da usare con `--to`. |
| `--to YYYY-MM-DD` | Data fine range (inclusa). Da usare con `--from`. |
| `--max-posts N` | Numero massimo di post (default: 0 = tutti). Si combina con entrambe le modalità. |
| `--output FILE` | File JSON di output personalizzato. |
| `--timeout SEC` | Timeout massimo di attesa per il run Apify (default: 300 secondi). Alzalo per range lunghi nel passato. |
| `--download-media` | Scarica anche immagini, video e PDF allegati ai post. |

**Nota sul tempo di esecuzione:** Il run Apify può richiedere da 30 secondi a diversi minuti. Durante l'attesa, lo script stampa un punto ogni 10 secondi. Informa l'utente che stai aspettando.

**Nota sull'output:** Lo script salva nel JSON l'item *completo* restituito dall'actor — testo del post (`content`), autore, engagement (likes, commenti, condivisioni, breakdown reazioni), URL canonico, media. Non c'è bisogno di chiamarlo di nuovo per recuperare campi mancanti: ci sono già tutti. Per la struttura completa vedi `references/apify-actor.md`.

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

## Esempi di interazione

**Esempio 1 — ultimi N post:**

> Utente: "Scarica gli ultimi 10 post di Nome Azienda da LinkedIn"

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --posted-limit any \
  --max-posts 10
```

**Esempio 2 — ultimo mese:**

> Utente: "Voglio i post di Nome Azienda dell'ultimo mese"

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --posted-limit month
```

**Esempio 3 — mese specifico nel calendario:**

> Utente: "Prendi i post di Nome Azienda di aprile 2026"

```bash
python3 scripts/fetch_posts.py \
  --company "nome-azienda" \
  --from 2026-04-01 \
  --to 2026-04-30
```

## Riferimenti tecnici

Per i dettagli sui parametri dell'actor Apify, la struttura del dataset e la mappatura degli endpoint REST, consulta `references/apify-actor.md`.
