import time
import requests
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# ================= CONFIG =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

EVENT_URLS = [
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-28-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-30-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-31-10"
]

CHECK_INTERVAL = 10
LOG_INTERVAL = 10
REPORT_INTERVAL = 100

contador = 0
status_anterior = {}

# ================= TELEGRAM =================
def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Erro Telegram: {e}")

# ================= DRIVER =================
def criar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=pt-BR")

    options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ================= CORE =================
def checar_ingressos(driver):
    global contador, status_anterior

    status_atual = {}
    print(f"\n🔎 Verificação #{contador + 1}")

    for url in EVENT_URLS:
        try:
            driver.get(url)
            time.sleep(5)

            blocos = driver.find_elements(By.CSS_SELECTOR, "#rates .item-rate")
            print(f"URL: {url} | Blocos: {len(blocos)}")

            if len(blocos) == 0:
                if "ESGOTADO" in driver.page_source.upper():
                    status_atual[url] = "ESGOTADO"
                else:
                    status_atual[url] = "INDISPONÍVEL"
                continue

            for bloco in blocos:
                try:
                    nome = bloco.find_element(By.TAG_NAME, "h5").text.strip()
                except:
                    nome = "Ingresso desconhecido"

                key = f"{url} | {nome}"

                try:
                    bloco.find_element(By.CLASS_NAME, "sold-out")
                    status = "ESGOTADO"
                except:
                    status = "DISPONÍVEL"

                status_atual[key] = status
                print(f"→ {nome}: {status}")

                if status == "DISPONÍVEL" and status_anterior.get(key) != "DISPONÍVEL":
                    print("🚨 DISPONÍVEL!")
                    enviar_telegram(f"🎟 DISPONÍVEL:\n{nome}\n{url}")

        except Exception as e:
            print(f"Erro ao acessar {url}: {e}")

    contador += 1
    status_anterior = status_atual.copy()

    # LOG
    if contador % LOG_INTERVAL == 0:
        print(f"\n===== LOG {contador} =====")
        for k, v in status_atual.items():
            print(f"{k} → {v}")
        print("=========================\n")

    # RELATÓRIO
    if contador % REPORT_INTERVAL == 0:
        print("📤 Enviando relatório...")
        relatorio = f"📊 Relatório ({contador} verificações):\n"
        for k, v in status_atual.items():
            relatorio += f"{k} → {v}\n"
        enviar_telegram(relatorio)

# ================= BOT THREAD =================
def iniciar_bot():
    driver = criar_driver()

    while True:
        try:
            checar_ingressos(driver)
        except Exception as e:
            print(f"Erro geral: {e}")
        time.sleep(CHECK_INTERVAL)

# ================= HTTP SERVER =================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def rodar_servidor():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"🌐 Servidor rodando na porta {port}")
    server.serve_forever()

# ================= MAIN =================
if __name__ == "__main__":
    print("🚀 Iniciando bot...")

    t = threading.Thread(target=iniciar_bot)
    t.daemon = True
    t.start()

    rodar_servidor()