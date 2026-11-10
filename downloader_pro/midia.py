"""Leitura de dados de arquivos de vídeo/áudio com o ffprobe."""
import json
import os
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


_duracoes = {}  # (caminho, data de modificação) -> segundos


def duracao_em_cache(caminho):
    """Duração (s) se este arquivo já foi lido antes; None se ainda não (não lê o arquivo)"""
    try:
        return _duracoes.get((caminho, os.path.getmtime(caminho)))
    except OSError:
        return 0.0


def duracao_arquivo(caminho):
    """Duração (s) do arquivo, lendo-o só na primeira vez (0 se não existir ou não puder ser lido)"""
    guardada = duracao_em_cache(caminho)
    if guardada is not None:
        return guardada
    duracao = info_midia(caminho)["duracao"]
    _duracoes[(caminho, os.path.getmtime(caminho))] = duracao
    return duracao
