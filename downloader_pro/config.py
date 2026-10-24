"""Pastas e constantes usadas pelo programa."""
import os
import sys

# No .exe (PyInstaller), __file__ aponta para uma pasta temporária: usa a pasta do próprio .exe.
# Rodando pelo Python, a raiz do projeto é a pasta acima deste pacote (onde fica o main.py).
EXECUTAVEL = getattr(sys, "frozen", False)
PASTA_SCRIPT = (os.path.dirname(sys.executable) if EXECUTAVEL
                else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_VIDEOS = os.path.join(PASTA_SCRIPT, "Vídeos")
PASTA_CORTES = os.path.join(PASTA_SCRIPT, "Cortes")
PASTA_MUSICAS = os.path.join(PASTA_SCRIPT, "Músicas")

# No .exe o ícone vem empacotado (sys._MEIPASS); rodando pelo Python, fica ao lado do main.py
ICONE = os.path.join(getattr(sys, "_MEIPASS", PASTA_SCRIPT), "icone.ico")

EXT_AUDIO = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac")
EXT_VIDEO = (".mp4", ".mkv", ".webm", ".mov")

# Cookies que indicam que a conta está logada no YouTube
COOKIES_LOGIN = ("LOGIN_INFO", "SID", "__Secure-3PSID")

PASSOS_COOKIES = ("Para exportar de novo:\n"
                  "1. Abra uma janela anônima e faça login no YouTube\n"
                  "2. Abra youtube.com/robots.txt\n"
                  "3. Clique na extensão 'Get cookies.txt LOCALLY' → Export\n"
                  "4. Feche a janela anônima\n"
                  f"5. Substitua o arquivo de cookies nesta pasta:\n{PASTA_SCRIPT}")
