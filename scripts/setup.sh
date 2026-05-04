#!/bin/bash
#
# linkedin-fetch Setup Script
# Installa dipendenze Python e configura l'ambiente
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "── linkedin-fetch Setup ──"
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Errore: python3 non trovato"
    echo "   Installa Python 3.8 o superiore"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 8 ]]; then
    echo "❌ Errore: Python 3.8+ richiesto (trovato $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION trovato"

# Verifica pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ Errore: pip3 non trovato"
    exit 1
fi

# Installa dipendenze
echo ""
echo "Installazione dipendenze..."
pip3 install -r requirements.txt

echo ""
echo "✅ Dipendenze installate"

# Configura .env se non esiste
if [[ ! -f ".env" ]]; then
    echo ""
    echo "Configurazione .env..."
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        echo "✅ File .env creato"
        echo ""
        echo "⚠️  ATTENZIONE: devi inserire il tuo APIFY_API_TOKEN in .env"
        echo "   1. Apri .env con il tuo editor:"
        echo "      vi .env"
        echo "   2. Sostituisci 'APIFY_API_TOKEN=' con il tuo token:"
        echo "      APIFY_API_TOKEN=il_tuo_token_qui"
        echo "   3. Ottieni il token qui: https://console.apify.com/account/integrations"
    else
        echo "❌ Errore: .env.example non trovato"
        exit 1
    fi
else
    echo ""
    echo "✅ File .env già esistente"

    # Verifica se il token è configurato
    if ! grep -q "^APIFY_API_TOKEN=[^[:space:]]" .env; then
        echo "⚠️  ATTENZIONE: APIFY_API_TOKEN non configurato in .env"
        echo "   Per usare la skill, devi inserire il tuo token:"
        echo "   1. Apri .env con il tuo editor:"
        echo "      vi .env"
        echo "   2. Inserisci il tuo token:"
        echo "      APIFY_API_TOKEN=il_tuo_token_qui"
        echo "   3. Ottieni il token qui: https://console.apify.com/account/integrations"
    else
        echo "✅ APIFY_API_TOKEN configurato"
    fi
fi

echo ""
echo "── Setup completato ──"
echo ""
echo "Puoi ora eseguire:"
echo "  python3 fetch_posts.py --company anthropicresearch --posted-limit month"
