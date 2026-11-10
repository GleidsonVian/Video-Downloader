"""Conversão entre texto de tempo ('31:31') e segundos."""
import re


def para_segundos(texto):
    """Converte '31:31', '31,31', '1:02:05' ou '90' em segundos"""
    partes = re.split(r'[:,.]', texto.strip())
    segundos = 0
    for parte in partes:
        segundos = segundos * 60 + int(parte)
    return segundos


def formatar_tempo(segundos):
    """Converte segundos em '31m31s' (ou '1h02m05s'), usado nos nomes de arquivo"""
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def tempo_curto(segundos):
    """Converte segundos em '05:49' (ou '1:02:05'), o formato dos campos de início/fim"""
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def formatar_duracao(segundos):
    """Duração para ler na tela: 563 -> '9 min 23 s'; 45 -> '45 s'; 3720 -> '1 h 02 min'"""
    total = int(round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas} h {minutos:02d} min"
    return f"{minutos} min {seg:02d} s" if minutos else f"{seg} s"
