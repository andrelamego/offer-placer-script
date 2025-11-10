# src/bot.py
from __future__ import annotations

import time

from typing import Callable, Optional
from src.core.settings import Settings
from src.core.insercao_service import carregar_insercao
from src.core.log_insercoes_service import registrar_log_insercao
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from pathlib import Path

from src.settings.config import DESCRICAO_PADRAO
from src.core.models import ItemInsercao
from src.core.helpers import (
    carregar_itens,
    abrir_navegador,
    clicar,
    preencher_campo,
    selecionar_ng_select,
    selecionar_ng_select_com_fallback,
    upload_arquivo,
)

# type alias: função que bloqueia até o usuário confirmar o login
WaitForLoginCallback = Callable[[], None]

def navegar_para_formulario(driver, nome: str):
    """
    Fluxo fixo:
    Clicar em 'Sell' > 'Items' > selecionar jogo 'Steal a brainrot' > 'Next'
    Selecionar tipo 'Brainrot' e raridade 'Secret'.
    TODOS os seletores abaixo precisam ser ajustados com base no HTML real.
    """
    
    # Abrir dropdown da conta
    clicar(
        driver,
        By.XPATH,
        "//div[contains(@class,'profile-picture-container')]//img[contains(@class,'app-image')]",
        "avatar da conta"
    )

    # Clicar em "Sell"
    clicar(
        driver,
        By.XPATH,
        "//button[@aria-label='Sell']",
        "botão Sell"
    )

    # Clicar em "Items"
    clicar(
        driver,
        By.XPATH,
        "(//div[contains(@class,'category-select')]//h6[normalize-space()='Items']/ancestor::div[contains(@class,'category-select')])[3]",
        "botão Items"
    )
    
    # Abrir o dropdown de jogos (ng-select)
    clicar(
        driver, 
        By.CSS_SELECTOR, 
        "div.ng-select-container",
        "campo de seleção de jogo")

    # Selecionar o jogo "Steal a Brainrot"
    clicar(
        driver,
        By.XPATH,
        "//div[contains(@class,'ng-dropdown-panel')]//div[contains(@class,'ng-option') and normalize-space()='Steal a Brainrot']",
        "opção 'Steal a Brainrot'"
    )

    # Clicar em "Next"
    clicar(
        driver,
        By.XPATH,
        "//button[@aria-label='Next']",
        "botão Next"
    )
    
    # Selecionar tipo de item "Brainrot"
    selecionar_ng_select(driver, 2, "Brainrot", "Tipo de item")
    
    # Selecionar raridade "Secret"
    selecionar_ng_select(driver, 4, "Secret", "Raridade do item")
    
    
    
    # Selecionar brainrot específico "Steal a Brainrot"
    selecionar_ng_select_com_fallback(driver, 6, nome, "Other", "Nome do brainrot") 
    
    clicar(
        driver,
        By.XPATH,
        "//button[@data-testid='sell-page-find-item-next-button-hU48' or @aria-label='Next']",
        "botão Next (após selecionar item)"
    )


def selecionar_nome_item(driver, titulo_item: str):
    """
    Tenta selecionar o nome do item em um dropdown customizado (ng-select).
    Se não encontrar, seleciona 'Other'.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from src.settings.config import TEMPO_ESPERA
    import time

    try:
        # === 1️⃣ Abre o dropdown do nome do item ===
        dropdown = WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ng-select-container"))
        )
        dropdown.click()
        time.sleep(1)

        # === 2️⃣ Tenta encontrar uma opção que contenha o texto do título ===
        opcoes = driver.find_elements(By.CSS_SELECTOR, "div.ng-option")
        alvo = None
        for opcao in opcoes:
            texto = opcao.text.strip().lower()
            if titulo_item.strip().lower() in texto:
                alvo = opcao
                break

        if alvo:
            alvo.click()
            print(f"[OK] Opção '{titulo_item}' encontrada e selecionada.")
        else:
            print(f"[INFO] '{titulo_item}' não encontrado — selecionando 'Other'.")
            try:
                opcao_other = driver.find_element(
                    By.XPATH, "//div[contains(@class,'ng-option')][contains(.,'Other')]"
                )
                opcao_other.click()
                print("[OK] Opção 'Other' selecionada.")
            except NoSuchElementException:
                print("[ERRO] Nenhuma opção 'Other' encontrada no dropdown.")

    except TimeoutException:
        print("[ERRO] Dropdown do nome do item não encontrado.")


def preencher_formulario_item(driver, item: ItemInsercao):
    """
    Preenche o formulário do item:
    - Título
    - Foto (upload)
    - Descrição padrão
    - Delivery Time = 20 min
    - Quantidade
    - Preço
    - Marca as duas checkboxes
    - Clica em "Place Offer"
    """

    titulo = item.titulo
    foto = item.imgUrl
    quantidade = str(item.quantidade)
    preco = str(item.preco)

    # 2) Título
    preencher_campo(
        driver,
        By.XPATH,
        "(//textarea[@placeholder='Type here...'])[1]",
        titulo,
        descricao="Título"
    )

    # 3) Foto (upload)
    upload_arquivo(
        driver,
        By.CSS_SELECTOR,
        "input[type='file'][accept*='image']",
        foto,
        descricao="Upload da imagem do anúncio"
    )

    time.sleep(1)  # Pequena pausa para garantir upload

    # 4) Descrição (padrão)
    preencher_campo(
        driver,
        By.XPATH,
        "(//textarea[@placeholder='Type here...'])[2]",
        DESCRICAO_PADRAO,
        descricao="Descrição"
    )

    # 5) Delivery Time (20 min)
    selecionar_ng_select(
        driver,
        1,
        "20 min",
        "Delivery Time"
    )
    
    # 6) Quantidade
    preencher_campo(
        driver,
        By.XPATH,
        "(//span[contains(@class,'unit-label') and normalize-space()='unit']/preceding-sibling::input)[1]",
        quantidade,
        descricao="Quantidade (input ao lado de unit)"
    )

    # 7) Preço
    preencher_campo(
        driver,
        By.XPATH,
        "//input[@placeholder='Price']",
        preco,
        descricao="Preço"
    )

    # 8) Checkboxes (Terms of Service)
    clicar(
        driver,
        By.XPATH,
        "//input[@type='checkbox' and @aria-label='Terms of Service']",
        "checkbox 'Terms of Service'"
    )
    
    # 9) Checkbox Seller Rules
    clicar(
        driver,
        By.XPATH,
        "//input[@type='checkbox' and @aria-label='Seller Rules']",
        "checkbox 'Seller Rules'"
    )

    # 9) Botão "Place Offer"
    clicar(
        driver,
        By.XPATH,
        "//button[@data-testid='place-offer-button-3Iwy' or @aria-label='Place Offer']",
        "botão 'Place Offer'"
    )

    # Pequena pausa pra deixar a página processar
    time.sleep(8)


def executar_bot(wait_for_login_callback: Optional[WaitForLoginCallback] = None) -> None:
    """
    Fluxo principal da automação.

    - Carrega itens do CSV ATIVO;
    - Abre o navegador;
    - Pausa para login manual:
      - se wait_for_login_callback for passado, usa o popup da UI;
      - senão, usa input() no terminal (modo CLI);
    - Publica itens;
    - Registra log da inserção.
    """
    settings = Settings.load()

    itens = carregar_insercao(settings.csv_ativo_path)
    print(f"\n[INFO] {len(itens)} item(s) carregado(s) do CSV ativo: {settings.csv_ativo_path}")

    if not itens:
        print(
            "[WARN] Nenhum item encontrado no CSV ativo.\n"
            f"Verifique o arquivo em: {settings.csv_ativo_path}\n"
            "Dica: use a ação 'Nova Inserção' para criar e preencher o CSV antes de rodar o bot."
        )
        return

    driver = abrir_navegador(settings)

    # 3) PAUSA PARA LOGIN MANUAL
    if wait_for_login_callback is not None:
        # UI (CustomTkinter) vai abrir um popup e só devolver quando o usuário confirmar
        print("\n[LOGIN] Aguardando confirmação de login pela interface gráfica...")
        wait_for_login_callback()
    else:
        # fallback: modo terminal
        print("\n[LOGIN] Faça login manualmente no site na janela do navegador que abriu.")
        print("[LOGIN] Resolva o CAPTCHA (se aparecer) e deixe na tela onde tem o botão 'Sell'.")
        input("[LOGIN] Quando terminar o login e tudo estiver pronto, pressione ENTER aqui no terminal para continuar... ")

    log_path = None

    try:
        total = len(itens)
        for idx, item in enumerate(itens, start=1):
            print(f"\n=== Publicando item {idx}/{total}: {item.titulo} ===")
            navegar_para_formulario(driver, item.nome)
            preencher_formulario_item(driver, item)

        log_path = registrar_log_insercao(settings.csv_ativo_path)
        print(f"\n[LOG] Log da inserção registrado em: {log_path}")
    finally:
        print("\n[INFO] Fechando navegador...")
        driver.quit()
        if log_path:
            print(f"[INFO] Inserção finalizada. Snapshot disponível em: {log_path}")
