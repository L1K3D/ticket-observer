import time
import requests
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import platform
import logging
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# ================= CONFIG =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

EVENT_URLS = [
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-28-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-30-10",
    "https://www.ticketmaster.com.br/event/pre-venda-army-membership-bts-world-tour-arirang-31-10"
]

CHECK_INTERVAL = 15
LOG_INTERVAL = 10
REPORT_INTERVAL = 100

contador = 0
status_anterior = {}
alertas_enviados = set()

logging.basicConfig(level=logging.INFO)

# ================= TELEGRAM PREMIUM =================
def enviar_telegram_premium(titulo, url, precos):
    try:
        precos_txt = "\n".join([f"💰 {p}" for p in precos]) if precos else "💰 Não identificado"

        texto = f"""
<b>🎟 INGRESSOS DISPONÍVEIS!</b>

<b>🎤 Evento:</b> {titulo}

{precos_txt}

⚡ Corre antes que acabe!
"""

        payload = {
            "chat_id": CHAT_ID,
            "text": texto,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "🎟 Comprar agora", "url": url}]
                ]
            }
        }

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json=payload,
            timeout=10
        )

    except Exception as e:
        logging.info(f"Erro Telegram: {e}")

# ================= DRIVER =================
def criar_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    sistema = platform.system()

    if sistema == "Linux":
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service()

    return webdriver.Chrome(service=service, options=options)

# ================= CORE =================
def checar_ingressos(driver):
    global contador, status_anterior, alertas_enviados

    status_atual = {}
    logging.info(f"\n🔎 Verificação #{contador + 1}")

    for url in EVENT_URLS:
        try:
            driver.get(url)
            time.sleep(5)

            # ===== ENTRA EM TODOS IFRAMES POSSÍVEIS =====
            encontrou = False
            iframes = driver.find_elements(By.TAG_NAME, "iframe")

            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(2)

                    botoes = driver.find_elements(By.XPATH, "//button[contains(., '+')]")

                    if len(botoes) > 0:
                        encontrou = True
                        logging.info("✅ Iframe correto encontrado")
                        break

                    driver.switch_to.default_content()

                except:
                    driver.switch_to.default_content()

            time.sleep(2)

            body = driver.page_source

            # ===== EXTRAÇÃO DE PREÇOS =====
            precos = re.findall(r"R\$\s?\d+[.,]?\d*", body)
            precos = list(set(precos))  # remove duplicados

            # ===== DETECÇÃO =====
            botoes = driver.find_elements(By.XPATH, "//button[contains(., '+')]")

            if len(botoes) > 0:
                status = "DISPONÍVEL"
            else:
                texto = body.upper()
                if "ESGOTADO" in texto:
                    status = "ESGOTADO"
                elif "R$" in texto:
                    status = "DISPONÍVEL"
                else:
                    status = "INDISPONÍVEL"

            status_atual[url] = status
            logging.info(f"{url} → {status}")

            # ===== ALERTA ABSURDO =====
            if status == "DISPONÍVEL" and url not in alertas_enviados:
                titulo = url.split("/")[-1].replace("-", " ").upper()

                logging.info("🚨 ALERTA ENVIADO!")

                enviar_telegram_premium(
                    titulo=titulo,
                    url=url,
                    precos=precos
                )

                alertas_enviados.add(url)

        except Exception as e:
            logging.info(f"Erro ao acessar {url}: {e}")

        finally:
            try:
                driver.switch_to.default_content()
            except:
                pass

    contador += 1
    status_anterior = status_atual.copy()

    # ===== LOG =====
    if contador % LOG_INTERVAL == 0:
        enviar_telegram_premium(
            titulo="📊 LOG",
            url="",
            precos=[f"{k} → {v}" for k, v in status_atual.items()]
        )

    # ===== RELATÓRIO =====
    if contador % REPORT_INTERVAL == 0:
        enviar_telegram_premium(
            titulo="📊 RELATÓRIO COMPLETO",
            url="",
            precos=[f"{k} → {v}" for k, v in status_atual.items()]
        )

# ================= BOT THREAD =================
def iniciar_bot():
    logging.info("🔥 Bot iniciado")
    driver = criar_driver()

    while True:
        try:
            checar_ingressos(driver)
        except Exception as e:
            logging.info(f"Erro geral: {e}")

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

    logging.info(f"🌐 Servidor na porta {port}")
    server.serve_forever()

# ================= MAIN =================
if __name__ == "__main__":
    logging.info("🚀 Iniciando bot...")

    
    t = threading.Thread(target=iniciar_bot)
    t.daemon = True
    t.start()

    rodar_servidor()