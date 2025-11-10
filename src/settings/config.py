# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from pathlib import Path

# Caminho base do projeto (pasta onde está este arquivo)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = DATA_DIR / "img"

# Caminho do CSV com os itens
CSV_PATH = BASE_DIR / "data" / "items.csv"

# URL inicial do site onde o bot vai operar
SITE_URL = "https://www.eldorado.gg/"



# Descrição padrão para todos os itens
DESCRICAO_PADRAO = (
    """Item Delivery Instructions

    1. After payment, the seller will send a private server link via chat.
    2. Buyer must provide their in-game username for verification.
    3. Join the private server using the link provided.
    4. Locate and steal the Brainrot pet that matches your purchase.
    5. Bring the Brainrot back to your base.
    6. Once the pet is secured in your base, the transaction is considered successful.
    -- Don't be a dumb trying to scam me. I record all times.

    Fast – Easy – Secure

    Thank you for your purchase!

    Ignore;
    Tags:
    RAINBOW-GOLD-DIAMOND-BLOODROOT-GALAXY-BLOODROT-Secret-La Grande-Garama-Los Combinasionas-Chicleteira Bicicleteira-Graipuss Medussi-La Vacca-Tralalero Tralala-Los-Rainbow-Dragon-Pot Hotspot-Nuclearo-Ban Hammer-HD Admin-Matteo-Esok-Ketupat-Noo my hotspotsitos-Sphagetti-Spag-toualetti-Sphageti-Burguro-Fryuro-Yin yang-dragon caneloni-Strawberry Elephant-Los 67
    """
)

# Tempo padrão de espera (segundos) para elementos aparecerem
TEMPO_ESPERA = 10

SELENIUM_PROFILE = r"C:\Users\andre\OneDrive\Área de Trabalho\chrome-selenium"

# Timeout padrão para esperar a intervenção humana (em segundos)
HUMAN_INTERVENTION_TIMEOUT = 12 * 5  # 5 minutos por padrão