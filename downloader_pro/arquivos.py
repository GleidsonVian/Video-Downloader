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


def formatar_tamanho(bytes_):
    """1536 -> '1,5 KB'; 1_500_000_000 -> '1,4 GB'"""
    valor = float(bytes_)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            return f"{valor:.0f} {unidade}" if unidade == "B" else f"{valor:.1f} {unidade}".replace(".", ",")
        valor /= 1024


def tamanho_de(caminho):
    """Tamanho em bytes de um arquivo, ou de uma pasta inteira"""
    if os.path.isfile(caminho):
        return os.path.getsize(caminho)
    return sum(os.path.getsize(os.path.join(raiz, nome))
               for raiz, _, nomes in os.walk(caminho) for nome in nomes)


def enviar_para_lixeira(caminho):
    """Manda o arquivo ou pasta para a Lixeira do Windows (dá para restaurar). Retorna True se deu certo.

    Sem a opção de "não confirmar": se o item for grande demais para a Lixeira, o próprio Windows
    avisa que seria apagado de vez e deixa o usuário decidir.
    """
    if platform.system() != "Windows":
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE, FOF_ALLOWUNDO = 3, 0x40
    operacao = SHFILEOPSTRUCTW(None, FO_DELETE, os.path.abspath(caminho) + "\0", None, FOF_ALLOWUNDO,
                               False, None, None)
    resultado = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operacao))
    return resultado == 0 and not operacao.fAnyOperationsAborted


def abrir_pasta(caminho):
    """Abre a pasta no explorador de arquivos"""
    if platform.system() == "Windows":
        os.startfile(caminho)
    elif platform.system() == "Darwin":  # macOS
        os.system(f'open "{caminho}"')
    else:  # Linux
        os.system(f'xdg-open "{caminho}"')
