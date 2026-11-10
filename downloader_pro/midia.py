"""Leitura de dados de arquivos de vídeo/áudio com o ffprobe."""
import json
import subprocess

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def info_midia(caminho):
    """Dados de um arquivo: {'duracao' (s), 'largura', 'altura', 'audio' (tem trilha de áudio?)}"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", caminho],
        capture_output=True, text=True, timeout=30, creationflags=SEM_JANELA)
    try:
        dados = json.loads(r.stdout or "{}")
    except ValueError:
        dados = {}
    streams = dados.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {"duracao": float(dados.get("format", {}).get("duration") or 0),
            "largura": video.get("width", 0), "altura": video.get("height", 0),
            "audio": any(s.get("codec_type") == "audio" for s in streams)}
