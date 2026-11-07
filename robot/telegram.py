"""
ROJAS TRABAJA - Publica las ofertas nuevas en el canal de Telegram.
Necesita los secrets TELEGRAM_TOKEN y TELEGRAM_CANAL en GitHub.
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.join(os.path.dirname(__file__), "..")
OFERTAS = os.path.join(BASE, "data", "ofertas.json")
ENVIADAS = os.path.join(BASE, "data", "telegram.json")
CONFIG = os.path.join(BASE, "config.js")
SITIO = "https:/" + "/marianojadur0-boop.github" + ".io/Rojas-Trabaja/"
MAX_POR_ENVIO = 25
ZONA = ["rojas", "pergamino", "junin", "salto", "colon", "arrecifes", "chacabuco", "rafael obligado",
        "carabelas", "los indios", "hunter", "la beba", "sol de mayo"]
log = lambda *a: print(*a, file=sys.stderr)


def pedir(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "RojasTrabaja/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8")


def api_url():
    try:
        txt = open(CONFIG, encoding="utf-8").read()
        m = re.search(r"API_URL\s*:\s*(.+?)\s*[,}\n]", txt)
        return "".join(re.findall(r'"([^"]*)"', m.group(1))) if m else ""
    except Exception:
        return ""


def ofertas_robot():
    try:
        d = json.load(open(OFERTAS, encoding="utf-8"))
    except Exception:
        return []
    return [{"clave": o["url"], "puesto": o.get("titulo"), "empresa": o.get("empresa"), "localidad": o.get("localidad"),
             "rubro": o.get("rubro"), "url": o["url"], "fecha": o.get("fecha"), "propia": False}
            for o in d.get("ofertas", []) if o.get("url")]


def ofertas_web():
    url = api_url()
    if not url.startswith("https:"):
        return []
    try:
        d = json.loads(pedir(url + "?tipo=ofertas"))
    except Exception as e:
        log("No se pudo leer la planilla:", e); return []
    return [{"clave": "web:" + str(o["id"]), "puesto": o.get("puesto"), "empresa": o.get("empresa"),
             "localidad": o.get("localidad"), "rubro": o.get("rubro"), "url": SITIO + "#ofertas",
             "fecha": o.get("fecha"), "propia": True, "primer_empleo": o.get("primer_empleo")}
            for o in d.get("items", []) if o.get("id")]


def en_zona(o):
    loc = (o.get("localidad") or "").lower().replace("í", "i").replace("ó", "o")
    return any(z in loc for z in ZONA)


def linea(o):
    e = lambda s: html.escape(str(s or ""), quote=True)
    extra = " · Primer empleo" if o.get("primer_empleo") else ""
    boton = "Postularme en Rojas Trabaja" if o["propia"] else "Ver oferta"
    return (f"💼 <b>{e(o['puesto'])}</b>\n🏢 {e(o['empresa'])}\n📍 {e(o['localidad'])} · {e(o['rubro'])}{e(extra)}\n"
            f"🔗 <a href=\"{e(o['url'])}\">{boton}</a>")


def mandar(token, canal, texto):
    datos = urllib.parse.urlencode({"chat_id": canal, "text": texto, "parse_mode": "HTML",
                                    "disable_web_page_preview": "true"}).encode()
    r = json.loads(pedir("https:/" + "/api.telegram" + ".org/bot" + token + "/sendMessage", datos))
    if not r.get("ok"):
        raise RuntimeError(r.get("description"))


def main():
    token, canal = os.environ.get("TELEGRAM_TOKEN", "").strip(), os.environ.get("TELEGRAM_CANAL", "").strip()
    if not token or not canal:
        log("Telegram sin configurar: no se manda nada."); return
    if not canal.startswith("@") and not canal.lstrip("-").isdigit():
        canal = "@" + canal
    try:
        enviadas = json.load(open(ENVIADAS, encoding="utf-8"))
    except Exception:
        enviadas = []
    ya = set(enviadas)

    todas = ofertas_web() + ofertas_robot()
    nuevas = [o for o in todas if o["clave"] not in ya and o.get("puesto")]
    nuevas.sort(key=lambda o: str(o.get("fecha") or ""), reverse=True)
    nuevas.sort(key=lambda o: 0 if o["propia"] else (1 if en_zona(o) else 2))
    elegidas = nuevas[:MAX_POR_ENVIO]
    if not elegidas:
        log("No hay ofertas nuevas para Telegram."); return

    hoy = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m")
    cab = f"🆕 <b>Ofertas nuevas · {hoy}</b>"
    pie = f"\n\n👉 Más ofertas, filtros por zona y rubro: {SITIO}"
    bloques, actual = [], cab
    for o in elegidas:
        l = "\n\n" + linea(o)
        if len(actual) + len(l) + len(pie) > 3900:
            bloques.append(actual); actual = cab.replace("</b>", " (sigue)</b>")
        actual += l
    bloques.append(actual + pie)

    for b in bloques:
        mandar(token, canal, b); time.sleep(3)
    enviadas = (enviadas + [o["clave"] for o in nuevas])[-3000:]
    with open(ENVIADAS, "w", encoding="utf-8") as fh:
        json.dump(enviadas, fh, ensure_ascii=False)
    log(f"Telegram: {len(elegidas)} ofertas enviadas en {len(bloques)} mensaje(s).")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("Error con Telegram:", e)
