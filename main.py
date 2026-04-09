import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# Configurações do bot
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Links dos eventos BTS
EVENT_URLS = [
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-28-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-30-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-31-10"
]

contador = 0
status_ingressos = {}

def enviar_telegram(mensagem):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem}
    requests.post(url, data=payload)

def checar_ingressos(driver):
    """Verifica status dos ingressos em todas as páginas"""
    global contador, status_ingressos

    for url in EVENT_URLS:
        driver.get(url)

        try:
            # espera até que os blocos de ingresso apareçam
            blocos = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#rates .item-rate"))
            )
        except:
            print("⚠️ Nenhum ingresso encontrado nessa página ainda.")
            # Mesmo sem blocos, verificar se está esgotado
            if "ESGOTADO" in driver.page_source:
                status_ingressos["Pré-venda Army Membership"] = "ESGOTADO"
            else:
                status_ingressos["Pré-venda Army Membership"] = "INDISPONÍVEL"
            # Não continua, para permitir o log

        # Processa os blocos se encontrados
        if 'blocos' in locals() and blocos:
            for bloco in blocos:
                try:
                    nome_elem = bloco.find_element(By.TAG_NAME, "h5")
                    nome = nome_elem.text.strip()
                except:
                    nome = "Ingresso desconhecido"

                # tenta achar o span de esgotado
                try:
                    bloco.find_element(By.CLASS_NAME, "sold-out")
                    status = "ESGOTADO"
                except:
                    status = "DISPONÍVEL"
                    enviar_telegram(f"🎟 Ingresso disponível: {nome}\n{url}")

                status_ingressos[nome] = status

    contador += 1

    # Log no console a cada 10 verificações
    if contador % 10 == 0:
        print(f"\n===== LOG {contador} verificações =====")
        for ingresso, status in status_ingressos.items():
            print(f"- {ingresso}: {status}")
        print("=====================================\n")

    # Relatório no Telegram a cada 100 verificações
    if contador % 100 == 0:
        relatorio = f"📊 Relatório de {contador} verificações:\n"
        for ingresso, status in status_ingressos.items():
            relatorio += f"- {ingresso}: {status}\n"
        enviar_telegram(relatorio)

if __name__ == "__main__":
    # Configurações do Chrome headless (ideal pro Render)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        while True:
            checar_ingressos(driver)
            time.sleep(1)  # intervalo entre verificações
    finally:
        driver.quit()