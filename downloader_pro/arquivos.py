"""Operações com arquivos e pastas."""
import os
import platform
import re

from .config import EXT_AUDIO, PASTA_MUSICAS


def nome_de_arquivo(texto):
    """Remove caracteres que o Windows não aceita em nomes de arquivo"""
    texto = re.sub(r'[/\\|]', '-', texto)
    return re.sub(r'[<>:"?*\x00-\x1f]', '', texto).strip(" .")[:100]


def limpar_temporarios(caminho_video):
    """Apaga pedaços que sobraram de uma tentativa que falhou (ex: 'Aula.f140.m4a.part-Frag12')"""
    if not caminho_video:
        return
    pasta = os.path.dirname(caminho_video)
    titulo = os.path.splitext(os.path.basename(caminho_video))[0]
    try:
        for nome in os.listdir(pasta):
            if nome.startswith(titulo + ".") and (".part" in nome or nome.endswith(".ytdl") or ".temp." in nome):
                try:
                    os.remove(os.path.join(pasta, nome))
                except OSError:
                    pass
    except OSError:
        pass


def listar_musicas():
    """Músicas da pasta Músicas/, como {nome: caminho}"""
    if not os.path.isdir(PASTA_MUSICAS):
        return {}
    return {nome: os.path.join(PASTA_MUSICAS, nome) for nome in sorted(os.listdir(PASTA_MUSICAS))
            if nome.lower().endswith(EXT_AUDIO)}


def abrir_pasta(caminho):
    """Abre a pasta no explorador de arquivos"""
    if platform.system() == "Windows":
        os.startfile(caminho)
    elif platform.system() == "Darwin":  # macOS
        os.system(f'open "{caminho}"')
    else:  # Linux
        os.system(f'xdg-open "{caminho}"')
