# Actor Apify: harvestapi~linkedin-company-posts

Questo file documenta l'actor Apify usato da `fetch_posts.py`, basato sulla documentazione ufficiale dell'actor (`https://apify.com/harvestapi/linkedin-company-posts`).

## Identificativo

- **Actor ID:** `harvestapi~linkedin-company-posts`
- **Store URL:** https://apify.com/harvestapi/linkedin-company-posts
- **Pricing:** $1.50 / 1.000 post (pay-per-event)

## Parametri di input usati dallo script

L'actor accetta molti parametri (vedi [schema completo](https://apify.com/harvestapi/linkedin-company-posts) per la lista totale). Lo script ne usa solo questi:

| Parametro actor | Flag CLI | Tipo | Descrizione |
|-----------------|----------|------|-------------|
| `targetUrls` | `--company` (mappato) | `string[]` | URL LinkedIn della company. Lo script accetta uno **slug** (es. `google`, `anthropicresearch`) o un **URL completo**. Se passi lo slug, lo script costruisce automaticamente `https://www.linkedin.com/company/<slug>/`. **Attenzione:** lo slug LinkedIn potrebbe non coincidere col nome commerciale (es. `google` va bene, ma per Anthropic devi usare `anthropicresearch`, non `anthropic`). |
| `postedLimitDate` | `--from` | `string` | Data **limite inferiore**. L'actor scrolla il feed dal post più recente a ritroso e si ferma quando incontra un post antecedente a questa data. Formato `YYYY-MM-DD`. |
| `postedLimit` | `--posted-limit` | `string` | Finestra **temporale relativa** valutata lato actor durante lo scroll. Valori: `1h`, `24h`, `week`, `month`, `3months`, `6months`, `year`, `any`. |
| `maxPosts` | `--max-posts` | `number` | Massimo per URL. `0` = tutti. **Default actor: 10** (lo script lo forza a 0 se non specificato). |

`postedLimitDate` e `postedLimit` sono mutuamente esclusivi nel CLI dello script: una richiesta usa l'uno o l'altro, mai entrambi.

### Filtro upper-bound `--to`

L'actor **non espone un parametro di data fine**. Quando l'utente fornisce `--from`/`--to`, lo script:

1. passa `--from` come `postedLimitDate` all'actor (riduzione lato actor),
2. scarica tutti i post che l'actor ha trovato tra `from` e oggi,
3. filtra lato client quelli successivi a `--to`.

Conseguenza: per recuperare un range stretto in un'epoca lontana (es. "marzo 2024") l'actor deve comunque attraversare tutti i post da marzo 2024 a oggi. In quei casi il run può durare diversi minuti — considera di alzare `--timeout`.

### Parametri non usati (riferimento)

L'actor espone altri parametri che lo script non sfrutta. Sono qui solo per riferimento futuro:

- `includeQuotePosts`, `includeReposts` — booleani per includere/escludere quote-post e repost (default: tutti inclusi).
- `scrapeReactions` + `maxReactions` — recupera la lista delle reazioni come item separati nel dataset. **Ogni reazione è fatturata come post extra.**
- `scrapeComments` + `maxComments` + `commentsPostedLimit` — idem per i commenti.
- `postNestedReactions`, `postNestedComments` — embeddano reazioni/commenti dentro l'item del post (sconsigliati: rischio di superare il max item size dell'actor).

## Endpoint REST Apify usati

Lo script `fetch_posts.py` interagisce con tre endpoint:

1. **Avvio run:**
   ```
   POST https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={token}
   ```
   Body JSON con `targetUrls`, `maxPosts`, e uno tra `postedLimitDate` o `postedLimit`. Restituisce `runId` e `defaultDatasetId`.

2. **Polling stato:**
   ```
   GET https://api.apify.com/v2/actor-runs/{runId}?token={token}
   ```
   Stati: `RUNNING`, `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMED-OUT`.

3. **Download dataset:**
   ```
   GET https://api.apify.com/v2/datasets/{datasetId}/items?token={token}&limit=1000
   ```
   Restituisce un array JSON con i post.

## Struttura dell'output (item)

Lo script salva nel JSON finale **l'item completo restituito dall'actor**, senza proiezioni o rinomine. Significa che tutti i campi qui sotto sono presenti nel file di output.

I campi sono basati sul sample ufficiale dell'actor.

### Campi del post

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `type` | `string` | `"post"` per i post normali. |
| `id` | `string` | ID univoco LinkedIn del post (es. `"7329207003942125568"`). Usato come nome cartella in `--download-media`. |
| `linkedinUrl` | `string` | URL canonico del post su LinkedIn. |
| `content` | `string` | **Testo completo** del post. Può contenere link `https://lnkd.in/...`. Questo è il campo da leggere per analisi testuali, non `text`. |
| `postedAt` | `object` | `{ "timestamp": 1747419119821, "date": "2025-05-16T18:11:59.821Z", "postedAgoShort": "6d", "postedAgoText": "..." }`. Lo script legge `postedAt.date` per ordinare e filtrare. |

### Autore

| Campo | Descrizione |
|-------|-------------|
| `author.name` | Nome visualizzato dell'azienda o profilo. |
| `author.publicIdentifier` | Slug pubblico (es. `williamhgates`). |
| `author.universalName` | Identifier interno LinkedIn (può essere `null`). |
| `author.type` | `"profile"` o `"company"`. |
| `author.linkedinUrl` | URL del profilo/pagina. |
| `author.info` | Headline / descrizione breve. |
| `author.website`, `author.websiteLabel` | Link esterno + label. |
| `author.avatar` | `{ "url": "...", "width": N, "height": N, "expiresAt": <timestamp> }` |

### Engagement

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `engagement.likes` | `number` | Conteggio totale "mi piace" (somma di tutte le reazioni). |
| `engagement.comments` | `number` | Numero di commenti. |
| `engagement.shares` | `number` | Numero di condivisioni. |
| `engagement.reactions` | `array` | Breakdown per tipo: `[{ "type": "LIKE", "count": 2477 }, { "type": "EMPATHY", "count": 158 }, ...]`. Tipi visti: `LIKE`, `APPRECIATION`, `EMPATHY`, `PRAISE`, `INTEREST`, `ENTERTAINMENT`. |

### Contenuti multimediali

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `postImages` | `string[]` | URL delle immagini singole allegate al post. |
| `postVideo` | `object` | `{ "thumbnailUrl": "...", "videoUrl": "..." }` — anteprima e MP4 del video. Presente solo per post video. |
| `document` | `object` | Documento PDF / carosello LinkedIn: `{ "title": "...", "transcribedDocumentUrl": "...", "coverPages": [{ "width": N, "height": N, "imageUrls": ["..."] }], "totalPageCount": N }`. Lo script scarica `transcribedDocumentUrl` se presente; altrimenti le immagini delle `coverPages`. |

### Altri campi presenti nell'output

| Campo | Descrizione |
|-------|-------------|
| `socialContent` | Flag UI di LinkedIn (`hideCommentsCount`, `hideReactionsCount`, `shareUrl`, ecc.). Raramente utile, ma è nel JSON. |
| `reactions` | Lista delle reazioni (con autore di ciascuna). **Solo se l'actor è stato chiamato con `scrapeReactions: true` — la skill non lo fa.** |
| `comments` | Lista dei commenti (con testo, autore, timestamp). **Solo se `scrapeComments: true` — la skill non lo fa.** |

> **Nota:** la disponibilità esatta dei campi dipende dal tipo di post (testo / immagini / video / documento) e dall'azienda. Il codice usa pattern difensivi `(item.get(...) or {})`.

> **Attenzione URL temporanee:** le URL di immagini, video, avatar e documenti contengono token con `expiresAt` (qualche giorno). Se vuoi conservare i media, usa `--download-media` durante lo stesso run o subito dopo.

## Errori comuni dell'actor

| Sintomo | Causa probabile | Azione |
|---------|-----------------|--------|
| Run `FAILED` subito | URL azienda inesistente o pagina privata | Verifica lo slug o l'URL LinkedIn |
| Dataset vuoto | `postedLimitDate` troppo recente o nessun post nel periodo | Allarga il range di date o prova `--posted-limit year` |
| Run `TIMED-OUT` | LinkedIn ha rallentato/rifiutato lo scraping, oppure range troppo ampio | Riprova dopo qualche minuto; per range lunghi alza `--timeout` |
| HTTP 401 | Token Apify non valido o scaduto | Rigenera il token su https://console.apify.com/account/integrations |

## Link utili

- Console Apify (runs): https://console.apify.com/actors/runs
- Pagina actor: https://apify.com/harvestapi/linkedin-company-posts
- Documentazione API Apify: https://docs.apify.com/api/v2
