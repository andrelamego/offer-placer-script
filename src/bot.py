# src/bot.py

import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from pathlib import Path

from src.config import DESCRICAO_PADRAO
from src.helpers import (
    carregar_itens,
    abrir_navegador,
    clicar,
    preencher_campo,
    selecionar_ng_select,
    selecionar_ng_select_com_fallback,
    upload_arquivo,
)


def navegar_para_formulario(driver, titulo: str):
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
    selecionar_ng_select_com_fallback(driver, 6, titulo, "Other", "Nome do brainrot") #TODO: ajustar nome do item
    
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
    from src.config import TEMPO_ESPERA
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


def preencher_formulario_item(driver, item: dict):
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

    titulo = item["titulo"]
    foto = str(item["foto"])
    quantidade = str(item["quantidade"])
    preco = str(item["preco"])

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


def main():
    itens = carregar_itens()
    print(f"\n[INFO] {len(itens)} item(s) carregado(s) do CSV.")

    if not itens:
        print("Nenhum item encontrado no CSV. Verifique o arquivo em data/itens.csv.")
        return

    # 1) Abre o navegador (com o profile que você já configurou dentro de abrir_navegador)
    driver = abrir_navegador()

    # 2) PAUSA PARA LOGIN MANUAL (OPÇÃO 1)
    print("\n[LOGIN] Faça login manualmente no site na janela do navegador que abriu.")
    print("[LOGIN] Resolva o CAPTCHA (se aparecer) e deixe na tela onde tem o botão 'Sell'.")
    input("[LOGIN] Quando terminar o login e tudo estiver pronto, pressione ENTER aqui no terminal para continuar... ")

    try:
        # 3) Fluxo normal: publicar itens
        for idx, item in enumerate(itens, start=1):
            print(f"\n=== Publicando item {idx}/{len(itens)}: {item['titulo']} ===")
            navegar_para_formulario(driver, item['titulo'])
            preencher_formulario_item(driver, item)
            # Se depois de publicar voltar para outra tela, talvez precise
            # adaptar aqui como voltar para o início do fluxo.
    finally:
        print("\n[INFO] Fechando navegador...")
        driver.quit()


if __name__ == "__main__":
    main()
