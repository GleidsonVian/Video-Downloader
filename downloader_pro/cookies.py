"""Cookies do YouTube (evitam o bloqueio "Sign in to confirm you're not a bot")."""
import os
import time

from .config import COOKIES_LOGIN, PASTA_SCRIPT


def achar_cookies():
    """Procura na pasta do programa um arquivo terminado em cookies.txt (ex: www.youtube.com_cookies.txt)"""
    for nome in sorted(os.listdir(PASTA_SCRIPT)):
        if nome.lower().endswith("cookies.txt"):
            return os.path.join(PASTA_SCRIPT, nome)
    return None


def cookies_vencidos(caminho):
    """True se os cookies de login do arquivo já expiraram (ou não existem)"""
    expiracoes = []
    with open(caminho, encoding="utf-8", errors="ignore") as f:
        for linha in f:
            campos = linha.rstrip("\n").split("\t")
            if len(campos) == 7 and campos[5] in COOKIES_LOGIN:
                expiracoes.append(int(campos[4] or 0))
    # Expiração 0 = cookie de sessão, que não vence pela data
    return not expiracoes or any(0 < exp < time.time() for exp in expiracoes)


def firefox_instalado():
    return os.path.isdir(os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles"))


def texto_status():
    """(texto, cor) para mostrar na janela sobre a situação dos cookies"""
    arquivo = achar_cookies()
    if arquivo and cookies_vencidos(arquivo):
        return "⚠ Seus cookies do YouTube venceram — exporte de novo", "#c47a00"
    if arquivo:
        return "cookies.txt encontrado ✓", "gray"
    if firefox_instalado():
        return "Usando cookies do Firefox", "gray"
    return "Sem cookies (o YouTube pode bloquear)", "gray"
