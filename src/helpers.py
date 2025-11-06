# src/helpers.py

import os
import csv
import time
import undetected_chromedriver as uc

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

from webdriver_manager.chrome import ChromeDriverManager

from src.config import CSV_PATH, SITE_URL, TEMPO_ESPERA, SELENIUM_PROFILE, BASE_DIR


def carregar_itens():
    """
    Lê o arquivo CSV no formato:
    titulo,foto,descricao,quantidade,preco

    A coluna 'descricao' será ignorada, pois usamos uma descrição fixa.
    """
    itens = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
             # caminho que veio do CSV (por ex.: "data\img\losmobilis.png" ou "img\losmobilis.png")
            raw_foto = row["foto"]

            # remove barra inicial se tiver (\data\img -> data\img)
            raw_foto = raw_foto.lstrip(r"\/")

            # monta caminho absoluto partindo do BASE_DIR
            caminho_foto = (BASE_DIR / raw_foto).resolve()
            
            itens.append({
                "titulo": row["titulo"],
                "foto": str(caminho_foto),
                "quantidade": row["quantidade"],
                "preco": row["preco"],
            })
    return itens


def abrir_navegador(use_profile: bool = True):
    """
    Abre o Chrome com webdriver-manager. Se use_profile=True, usa SELENIUM_PROFILE.

    options = webdriver.ChromeOptions()

    if use_profile:
        # cria a pasta se não existir (Chrome criará arquivos nela)
        os.makedirs(SELENIUM_PROFILE, exist_ok=True)
        options.add_argument(f"--user-data-dir={SELENIUM_PROFILE}")

    # remove flags de automação (opcional)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    # navega para a url
    driver.get(SITE_URL)
    """    
    options = uc.ChromeOptions()
    
    options.user_data_dir = SELENIUM_PROFILE
    
    # Desativa o popup "Restaurar páginas"
    options.add_argument("--disable-session-crashed-bubble")
    
    driver = uc.Chrome(options=options)
    driver.maximize_window()
    driver.get(SITE_URL)
    
    return driver

    

def wait_for_manual_login_prompt():
    """
    Simples: pausa o script e pede ao usuário para fazer login manualmente
    e pressionar ENTER no terminal.
    """
    print("\n=== AÇÃO REQUERIDA: Faça login manualmente no navegador aberto. ===")
    input("Quando terminar o login, pressione ENTER para continuar...")


def clicar(driver, by: By, seletor: str, descricao: str = "elemento"):
    """
    Espera o elemento ficar clicável e clica.
    """
    time.sleep(0.5)
    
    elem = WebDriverWait(driver, TEMPO_ESPERA).until(
        EC.element_to_be_clickable((by, seletor))
    )
    elem.click()
    print(f"[OK] Cliquei em: {descricao}")
    return elem

def selecionar_ng_select(driver, indice: int, texto_opcao: str, descricao: str = "ng-select"):
    """
    Seleciona uma opção em um componente ng-select (Angular).

    - indice: posição do ng-select na página (1 = primeiro, 2 = segundo, ...)
    - texto_opcao: texto exato da opção, ex.: "Steal a Brainrot", "Brainrot", "Secret"
    - descricao: texto apenas para logs

    Exemplo de uso:
        selecionar_ng_select(driver, 1, "Steal a Brainrot", "jogo")
        selecionar_ng_select(driver, 2, "Brainrot", "tipo de item")
        selecionar_ng_select(driver, 3, "Secret", "raridade")
    """
    time.sleep(0.5)
    
    # 1) Abre o combobox (ng-select) pela posição
    xpath_container = f"(//div[contains(@class,'ng-select-container')])[{indice}]"
    clicar(
        driver,
        By.XPATH,
        xpath_container,
        f"{descricao} (abrir)"
    )

    # Pequena pausa opcional para garantir que o dropdown renderizou
    time.sleep(0.3)

    # 2) Espera a opção aparecer e ficar clicável
    xpath_opcao = (
        "//div[contains(@class,'ng-dropdown-panel')]"
        "//div[@role='option']//div[normalize-space()='" + texto_opcao + "']"
    )

    elem_opcao = WebDriverWait(driver, TEMPO_ESPERA).until(
        EC.element_to_be_clickable((By.XPATH, xpath_opcao))
    )
    elem_opcao.click()
    print(f"[OK] Selecionado '{texto_opcao}' em {descricao}")
    
    
def selecionar_ng_select_com_fallback(driver, indice: int, texto_opcao: str, fallback_opcao: str = "Other", descricao: str = "ng-select com fallback"):
    """
    Seleciona uma opção em um ng-select (Angular), com fallback automático.

    - indice: posição do ng-select na página (1 = primeiro, 2 = segundo, ...)
    - texto_opcao: texto principal que se deseja selecionar
    - fallback_opcao: texto da opção de fallback (ex: 'Other')
    - descricao: texto apenas para logs

    Exemplo:
        selecionar_ng_select_com_fallback(driver, 4, nome_item, "Other", "nome do item")
    """    
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    time.sleep(0.5)

    # Abre o combobox
    xpath_container = f"(//div[contains(@class,'ng-select-container')])[{indice}]"
    clicar(driver, By.XPATH, xpath_container, f"{descricao} (abrir)")

    time.sleep(0.3)

    # XPath para procurar a opção desejada
    xpath_opcao_desejada = (
        "//div[contains(@class,'ng-dropdown-panel')]"
        "//div[@role='option']//div[normalize-space()='" + texto_opcao + "']"
    )

    # XPath para o fallback (Other)
    xpath_opcao_fallback = (
        "//div[contains(@class,'ng-dropdown-panel')]"
        "//div[@role='option']//div[normalize-space()='" + fallback_opcao + "']"
    )

    try:
        # Tenta clicar na opção desejada
        elem = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, xpath_opcao_desejada))
        )
        elem.click()
        print(f"[OK] Selecionado '{texto_opcao}' em {descricao}")
        return True
    except TimeoutException:
        # Se não encontrou, tenta o fallback
        print(f"[INFO] '{texto_opcao}' não encontrado. Selecionando '{fallback_opcao}' em {descricao}...")

        try:
            elem_fallback = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_opcao_fallback))
            )
            elem_fallback.click()
            print(f"[OK] Selecionado fallback '{fallback_opcao}' em {descricao}")
            return False
        except TimeoutException:
            print(f"[ERRO] Nenhuma das opções ('{texto_opcao}' ou '{fallback_opcao}') encontrada em {descricao}.")
            return None


def upload_arquivo(driver, by: By, seletor: str, caminho_arquivo: str, descricao: str = "upload de arquivo"):
    """
    Envia um arquivo para um <input type="file"> usando send_keys.
    Funciona mesmo que o input esteja hidden.
    Faz checagem de caminho e imprime erros úteis.
    """
    time.sleep(0.5)  # pequeno delay se a UI for animada

    caminho = Path(caminho_arquivo)
    if not caminho.is_absolute():
        # vai até a raiz do projeto automaticamente
        base = Path(__file__).resolve().parent.parent
        caminho = base / caminho

    caminho = caminho.resolve()    
    
    if not caminho.exists():
        print(f"[ERRO] Arquivo para upload NÃO encontrado: {caminho}")
        return None

    try:
        elem_input = WebDriverWait(driver, TEMPO_ESPERA).until(
            EC.presence_of_element_located((by, seletor))
        )
    except TimeoutException:
        print(f"[ERRO] Não encontrei o input de upload ({descricao}).")
        print(f"       Seletor: {by} -> {seletor}")
        return None
    
    time.sleep(0.5)  # pequeno delay antes do send_keys

    try:
        elem_input.send_keys(str(caminho))
        print(f"[OK] {descricao}: {caminho}")
        return elem_input
    except Exception as e:
        print(f"[ERRO] Falha ao enviar arquivo para o input: {e}")
        return None


def preencher_campo(driver, by: By, seletor: str, valor: str, limpar: bool = True, descricao: str = "campo"):
    """
    Espera o campo ficar visível, opcionalmente limpa e preenche com 'valor'.
    """
    time.sleep(0.5)
    
    elem = WebDriverWait(driver, TEMPO_ESPERA).until(
        EC.visibility_of_element_located((by, seletor))
    )
    if limpar:
        elem.clear()
    elem.send_keys(valor)
    print(f"[OK] Preenchi {descricao} com: {valor}")
    return elem


def selecionar_dropdown_por_texto(driver, by: By, seletor: str, texto: str, descricao: str = "dropdown"):
    """
    Localiza um <select> e escolhe a opção pelo texto visível.
    """
    time.sleep(0.5)
    
    elem = WebDriverWait(driver, TEMPO_ESPERA).until(
        EC.presence_of_element_located((by, seletor))
    )
    select = Select(elem)
    select.select_by_visible_text(texto)
    print(f"[OK] Selecionei '{texto}' em {descricao}")
    return select
