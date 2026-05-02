# Actor Apify: harvestapi~linkedin-company-posts

Questo file documenta l'actor Apify usato da `fetch_posts.py`.

## Identificativo

- **Actor ID:** `harvestapi~linkedin-company-posts`
- **Store URL:** https://apify.com/harvestapi/linkedin-company-posts

## Parametri di input

L'actor accetta i seguenti parametri (passati via JSON nel body della chiamata POST):

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `targetUrls` | `string[]` | Sì | Lista di URL delle pagine LinkedIn aziendali (es. `["https://www.linkedin.com/company/nome-azienda/"]`). Supporta più URL in un unico run. |
| `postedLimitDate` | `string` | No | Data limite inferiore per i post, nel formato `YYYY-MM-DD`. L'actor scarta i post pubblicati prima di questa data. Nel nostro script corrisponde a `--from`. |
| `maxPosts` | `number` | No | Numero massimo di post da recuperare per ogni URL. `0` o omesso = nessun limite. Mappato su `--max-posts`. |

### Note sui parametri

- `postedLimitDate` filtra **lato actor**, quindi riduce il tempo di esecuzione quando si cerca un range ristretto.
- Il filtro `--to` (data fine) viene applicato **lato script** dopo aver scaricato il dataset, perché l'actor non espone un parametro di data fine.
- Se si vuole recuperare solo gli ultimi N post, conviene impostare un `postedLimitDate` molto indietro nel tempo (es. `2020-01-01`) e usare `maxPosts`.

## Endpoint API usati

Lo script `fetch_posts.py` interagisce con tre endpoint REST di Apify:

1. **Avvio run:**
   ```
   POST https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={token}
   ```
   Body JSON con i parametri di input sopra elencati.
   Restituisce `runId` e `defaultDatasetId`.

2. **Polling stato:**
   ```
   GET https://api.apify.com/v2/actor-runs/{runId}?token={token}
   ```
   Lo stato può essere `RUNNING`, `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMED-OUT`.

3. **Download dataset:**
   ```
   GET https://api.apify.com/v2/datasets/{datasetId}/items?token={token}&limit=1000
   ```
   Restituisce un array JSON con i post.

## Struttura dell'output (item)

Ogni elemento del dataset è un oggetto JSON con i campi principali:

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `postId` | `string` | ID univoco del post su LinkedIn |
| `postedAt` | `object` | `{ "date": "2026-04-15T09:30:00.000Z", "text": "15 April 2026 at 09:30" }` |
| `text` | `string` | Testo completo del post (può contenere HTML) |
| `url` | `string` | URL diretto al post su LinkedIn |
| `author` | `object` | `{ "name": "Nome Azienda", "url": "..." }` |
| `images` | `string[]` | URL delle immagini allegate |
| `reactions` | `number` | Conteggio totale reazioni |
| `comments` | `number` | Conteggio commenti |
| `shares` | `number` | Conteggie condivisioni |
| `reposts` | `number` | Conteggio repost |

> **Nota:** La disponibilità esatta dei campi dipende dalla versione dell'actor e dalla struttura della pagina LinkedIn. Alcuni campi possono mancare o essere `null`.

### Campi multimediali (struttura reale)

Oltre ai campi base, l'actor restituisce anche i seguenti blocchi per i contenuti multimediali:

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `postImages` | `string[]` | URL delle immagini singole allegate al post |
| `postVideo` | `object` | `{ "thumbnailUrl": "...", "videoUrl": "..." }` — URL video (MP4) e anteprima |
| `document` | `object` | Documento PDF allegato (es. caroselli LinkedIn): `{ "title": "...", "transcribedDocumentUrl": "...", "coverPages": [{ "imageUrls": ["..."] }], "totalPageCount": N }` |

> **Attenzione:** le URL multimediali contengono token con scadenza (`expiresAt`). Scaricale subito dopo il fetch se vuoi conservarle.

## Errori comuni dell'actor

| Sintomo | Causa probabile | Azione |
|---------|-----------------|--------|
| Run `FAILED` subito | URL azienda inesistente o pagina privata | Verifica lo slug o l'URL LinkedIn |
| Dataset vuoto | `postedLimitDate` troppo recente o nessun post nel periodo | Allarga il range di date |
| Run `TIMED-OUT` | LinkedIn ha rallentato/rifiutato lo scraping | Riprova dopo qualche minuto; se persiste, controlla i log su Apify Console |
| HTTP 401 | Token Apify non valido o scaduto | Rigenera il token su https://console.apify.com/account/integrations |

## Link utili

- Console Apify (runs): https://console.apify.com/actors/runs
- Documentazione API Apify: https://docs.apify.com/api/v2
