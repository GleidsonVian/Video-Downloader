"""Download de vídeo e áudio com o yt-dlp (sem nada de interface)."""
import os
import re
import subprocess
import sys

from .config import EXECUTAVEL, PASSOS_COOKIES, PASTA_MUSICAS, PASTA_SCRIPT, PASTA_VIDEOS
from .cookies import firefox_instalado

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

FORMATO_VIDEO = [
    # Prefere H.264 (avc1), que abre em qualquer player; senão o melhor MP4 até 1080p.
    "-f", ("bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
           "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"),
    "--merge-output-format", "mp4",
    # Evita o segundo passe lento do +faststart no Windows que costuma travar com antivírus/explorer
    "--postprocessor-args", "Merger:-movflags 0",
    "-o", os.path.join(PASTA_VIDEOS, "%(title)s.%(ext)s"),
]

# Só o áudio, em MP3 (um MP3 de música ocupa ~5 MB, contra centenas de MB do vídeo)
FORMATO_AUDIO = [
    "-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "192K",
    "--no-playlist", "-o", os.path.join(PASTA_MUSICAS, "%(title)s.%(ext)s"),
]


def baixar(url, paralelos, arquivo_cookies, somente_audio=False, ao_progresso=None, ao_iniciar=None):
    """Baixa com o yt-dlp num processo separado. Retorna (caminho_final, erro, avisos).

    Processo separado porque, quando o download falha no meio, o yt-dlp pode deixar arquivos
    abertos; ao fim do processo o Windows libera tudo e a próxima tentativa continua de onde parou.

    ao_progresso(percentual) é chamado enquanto baixa; ao_iniciar(processo) recebe o processo
    (e None quando termina), para quem chama poder cancelá-lo.
    """
    # No .exe não há Python separado: o próprio .exe roda o yt-dlp (veja main.py)
    rodar = [sys.executable, "--ytdlp"] if EXECUTAVEL else [sys.executable, "-m", "yt_dlp"]
    comando = [
        *rodar, "--newline", "--no-colors", "--progress",
        *(FORMATO_AUDIO if somente_audio else FORMATO_VIDEO),
        # Vídeos que foram lives vêm em centenas de pedaços: baixa vários de cada vez
        "--concurrent-fragments", str(paralelos),
        # O YouTube exige um runtime JavaScript; usa o Node.js instalado
        "--js-runtimes", "node",
        "--progress-template", "download:PROGRESSO %(progress._percent_str)s",
        "--print", "after_move:ARQUIVO %(filepath)s",
    ]
    # Cookies evitam o "confirm you're not a bot": usa cookies.txt se existir, senão os do Firefox.
    # (Chrome e Edge criptografam os cookies e o yt-dlp não consegue lê-los.)
    if arquivo_cookies:
        comando += ["--cookies", arquivo_cookies]
    elif firefox_instalado():
        comando += ["--cookies-from-browser", "firefox"]
    comando.append(url)

    processo = subprocess.Popen(
        comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=SEM_JANELA)
    if ao_iniciar:
        ao_iniciar(processo)
    caminho, erros, avisos = None, [], []
    try:
        for linha in processo.stdout:
            linha = linha.strip()
            if linha.startswith("PROGRESSO"):
                try:
                    if ao_progresso:
                        ao_progresso(float(linha.split()[-1].rstrip("%")))
                except ValueError:
                    pass
            elif linha.startswith("ARQUIVO "):
                caminho = linha[len("ARQUIVO "):]
            elif linha.startswith("ERROR:"):
                erros.append(linha)
            elif linha.startswith("WARNING:"):
                avisos.append(linha)
        processo.wait()
    finally:
        if ao_iniciar:
            ao_iniciar(None)
    erro = None if processo.returncode == 0 and caminho else ("\n".join(erros) or "O download falhou sem mensagem de erro")
    return caminho, erro, avisos


def dica_do_erro(erro, tem_cookies):
    """Texto explicando o que fazer, de acordo com o erro do yt-dlp"""
    erro = re.sub(r'\x1b\[[0-9;]*m', '', erro)
    if "live event" in erro:
        return ("Esse link é de uma live que acabou de terminar.\n"
                "O YouTube ainda está processando o vídeo; tente de novo mais tarde.")
    if "timed out" in erro.lower() or "connection" in erro.lower():
        return ("A conexão com o YouTube travou.\n"
                "Clique em baixar de novo: o download continua de onde parou.")
    if "No video formats" in erro or "reloaded" in erro:
        return 'Atualize o yt-dlp: python -m pip install -U "yt-dlp[default]"'
    if "not a bot" in erro or "429" in erro:
        if tem_cookies:
            return "Seus cookies do YouTube venceram ou foram invalidados.\n\n" + PASSOS_COOKIES
        return ("O YouTube bloqueou o acesso sem login.\n\n"
                "Faça login no YouTube pelo Firefox e tente de novo,\n"
                f"ou salve um cookies.txt do YouTube nesta pasta:\n{PASTA_SCRIPT}")
    return "Verifique se o FFmpeg está instalado."
