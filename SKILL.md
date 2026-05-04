---
name: linkedin-fetch
description: Recupera post da pagine LinkedIn aziendali. Finestre temporali (24h, settimana, mese) o range espliciti. Scarica media con --download-media. Usa --company con lo slug LinkedIn (es. 'google', non 'Google').
---

Questa skill orchestra `fetch_posts.py` per recuperare post da una pagina LinkedIn aziendale tramite Apify e salvarli in un file JSON locale.

## Prerequisiti

Prima di eseguire lo script, prepara l'ambiente:

1. **Installa dipendenze** — Usa lo script di setup:
   ```bash
   python3 scripts/setup.sh
   ```
   Oppure installa manualmente:
   ```bash
   pip install -r scripts/requirements.txt
   ```

2. **Configura il token Apify** — Lo script legge `APIFY_API_TOKEN` dal file `scripts/.env` o dalle variabili d'ambiente. Se usi `setup.sh`, viene creato un file `.env` da compilare.

   Ottieni il token su: https://console.apify.com/account/integrations

Se durante l'esecuzione compare "Errore: APIFY_API_TOKEN non trovato", guida l'utente a configurarlo prima di riprovare.

## Verifica

Dopo l'installazione, esegui il test per verificare che tutto funzioni:

```bash
python3 scripts/test.py
```

Il test recupera 2 post da `anthropicresearch` e verifica che l'output JSON sia valido.

## Flusso in 3 passi

### 1. Raccogli i parametri dall'utente

Prima di eseguire qualsiasi comando, chiedi (se non già forniti nel messaggio):

- **URL** della pagina LinkedIn (es. `https://www.linkedin.com/company/nome-azienda/` oppure solo lo slug `nome-azienda`)
- **Quale finestra temporale**: ultimi N post, ultime 24h/settimana/mese, oppure un range di date specifico.

Se l'utente fornisce già URL e parametri nel messaggio originale, salta le domande e procedi direttamente.

**Pattern URL → slug:** Se l'utente passa un URL completo come `https://www.linkedin.com/company/nome-azienda/`, estrai lo slug (`nome-azienda`) e passalo a `--company`. Lo script accetta sia URL che slug, ma passare lo slug è più pulito.

**Importante — lo slug LinkedIn potrebbe non coincidere col nome commerciale:**

Lo slug è l'ultima parte dell'URL della pagina LinkedIn, non sempre uguale al nome "popolare" dell'azienda. Esempi:

| Nome commerciale | Slug LinkedIn |
|------------------|---------------|
| Anthropic | `anthropicresearch` |
| Google | `google` |
| Meta | `meta` |
| Netflix | `netflix` |
| Spotify | `spotify` |
| Microsoft | `microsoft` |

**Risoluzione slug in 3 livelli:**

1. **Tenta lo slug ingenuo** — passa `--company <nome_in_lowercase>`. Nella maggior parte dei casi funziona: `google`, `microsoft`, `netflix`, `spotify`, `meta` coincidono col nome commerciale.

2. **Se il run fallisce con 404** — lo slug non coincide. Invece di chiedere all'utente, esegui:
   ```bash
   python3 scripts/search_company.py --query "<nome azienda>"
   ```
   Questo chiama l'actor `harvestapi/linkedin-company-search` che cerca l'azienda su LinkedIn e restituisce un JSON con i risultati. Ogni risultato contiene: `universalName` (lo slug), `name`, `linkedinUrl`, `employeeCount`, `followerCount`, `description`, `locations` (city, country).

3. **Interpreta i risultati:**
   - **Risultato unico** → usa `universalName` come `--company`
   - **Risultati multipli** → mostra le opzioni all'utente con nome, dipendenti, follower e location; chiedi quale scegliere
   - **Nessun risultato** → informa l'utente che l'azienda non è stata trovata su LinkedIn

   **Esempio:** per "LYBRA", lo script restituisce `lybra-consulting` (Padova, 10 dip, 1.803 follower), `lybra-tech` (Zucchetti, Roma, 23 dip), `lybra-destination` (Zucchetti, Roma). Mostri le opzioni e chiedi conferma.

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
| `--output FILE` | File JSON di output personalizzato. Se passi un file `.json`, lo script crea automaticamente una cartella `<nome>_media/` con dentro il JSON e gli eventuali media. Se omesso, usa `linkedin_posts_<slug>/` nella directory corrente. |
| `--timeout SEC` | Timeout massimo di attesa per il run Apify (default: 300 secondi). **Non aggiungerlo** per richieste standard (ultime 24h, settimana, mese). Alzalo solo per range espliciti oltre 3 mesi nel passato (es. "aprile 2024"). |
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
| Errore: dipendenza Python mancante | `apify-client` o `python-dotenv` non installati | Esegui `python3 scripts/setup.sh` |
| Errore: APIFY_API_TOKEN non trovato | Token non configurato | Guida l'utente a crearlo su https://console.apify.com/account/integrations e a scriverlo in `scripts/.env` |
| Errore 401 Apify | `APIFY_API_TOKEN` non valido | Verifica che il token sia corretto e non scaduto |
| RUN FAILED / TIMED-OUT | Apify non è riuscito a completare lo scraping | Controlla i log su `https://console.apify.com/actors/runs/<run_id>` |
| URL non trovato | Slug azienda errato | Verifica lo slug copiandolo dall'URL LinkedIn (`https://www.linkedin.com/company/→slug←`) |
| Nessun post trovato | Range di date senza post | Allarga il range o controlla che la pagina sia attiva |

## Esempi di interazione

**Esempio 1 — ultimi N post:**

> Utente: "Scarica gli ultimi 10 post di Nome Azienda da LinkedIn"

Prima di eseguire, verifica lo slug LinkedIn dell'azienda (l'ultima parte dell'URL, es. `anthropicresearch` per Anthropic). Se l'utente fornisce il nome commerciale, chiedi conferma o cerca lo slug corretto.

```bash
python3 scripts/fetch_posts.py \
  --company "slug-esatto" \
  --posted-limit any \
  --max-posts 10
```

**Esempio 2 — ultimo mese:**

> Utente: "Voglio i post di Nome Azienda dell'ultimo mese"

Assicurati di usare lo slug LinkedIn corretto (es. `anthropicresearch`, non `anthropic`):

```bash
python3 scripts/fetch_posts.py \
  --company "slug-esatto" \
  --posted-limit month
```

**Esempio 3 — mese specifico nel calendario:**

> Utente: "Prendi i post di Nome Azienda di aprile 2026"

Usa lo slug LinkedIn corretto:

```bash
python3 scripts/fetch_posts.py \
  --company "slug-esatto" \
  --from 2026-04-01 \
  --to 2026-04-30
```

**Esempio 4 — verifica installazione:**

> Per verificare che tutto funzioni dopo l'installazione:

```bash
python3 scripts/test.py
```

## Riferimenti tecnici

Per i dettagli sui parametri dell'actor Apify, la struttura del dataset e la mappatura degli endpoint REST, consulta `references/apify-actor.md`.
