"""Trilha de música de fundo: várias músicas em sequência, com transição suave e repetição (sem interface)."""
import os

from .midia import info_midia
from .tempos import tempo_curto

FADE_MUSICA = 2.0  # segundos de transição entre uma música e a próxima


def como_lista(musica):
    """Aceita uma música (texto) ou várias (lista) e devolve sempre uma lista"""
    if not musica:
        return []
    return [musica] if isinstance(musica, str) else list(musica)


def validar(musicas):
    """Levanta RuntimeError se não há música escolhida ou algum arquivo sumiu"""
    if not musicas:
        raise RuntimeError("Escolha pelo menos uma música em \"Áudio do corte\" (ou use o áudio original).")
    for caminho in musicas:
        if not os.path.exists(caminho):
            raise RuntimeError(f"A música não existe mais:\n{caminho}")


def planejar(musicas, inicio, total):
    """Quais pedaços de música tocar, em ordem, para cobrir 'total' segundos.

    As músicas tocam na ordem da lista e, se a lista acabar antes do fim, ela recomeça. Cada música se
    funde com a seguinte (transição de 'fade' segundos). 'inicio' vale só para a primeira música.
    Retorna ([(caminho, início, duração)], fade).
    """
    duracoes = {}
    for caminho in dict.fromkeys(musicas):
        duracao = info_midia(caminho)["duracao"]
        if duracao <= 0:
            raise RuntimeError(f"Não consegui ler a música:\n{os.path.basename(caminho)}")
        duracoes[caminho] = duracao
    primeira = musicas[0]
    if inicio >= duracoes[primeira] - 3:
        raise RuntimeError(f"A música \"{os.path.basename(primeira)}\" tem {tempo_curto(duracoes[primeira])}; "
                           f"o \"Começar em\" ({tempo_curto(inicio)}) passa disso.")
    # A transição não pode ser maior que um terço da música mais curta (ou do que sobra da primeira)
    fade = min(FADE_MUSICA, min(duracoes.values()) / 3, (duracoes[primeira] - inicio) / 3)

    pedacos, coberto = [], 0.0
    while coberto < total and len(pedacos) < 500:
        i = len(pedacos)
        caminho = musicas[i % len(musicas)]
        comeco = inicio if i == 0 else 0
        sobreposicao = fade if pedacos else 0
        precisa = total - coberto + sobreposicao  # quanto esta música precisa tocar para fechar o tempo
        duracao = min(duracoes[caminho] - comeco, max(precisa, fade * 2))
        pedacos.append((caminho, comeco, round(duracao, 2)))
        coberto += duracao - sobreposicao
    return pedacos, fade


def montar_trilha(musicas, inicio, total, primeira_entrada):
    """Entradas e filtro do ffmpeg que montam a trilha com 'total' segundos, no rótulo [musica].

    'primeira_entrada' é o índice da primeira entrada de música na linha de comando do ffmpeg.
    Retorna (argumentos das entradas, filtro).
    """
    validar(musicas)
    pedacos, fade = planejar(musicas, inicio, total)
    argumentos, filtro = [], []
    for j, (caminho, comeco, duracao) in enumerate(pedacos):
        argumentos += ["-ss", str(comeco), "-t", str(duracao), "-i", caminho]
        filtro.append(f"[{primeira_entrada + j}:a]aresample=48000,asetpts=PTS-STARTPTS,"
                      f"aformat=channel_layouts=stereo[m{j}]")
    atual = "[m0]"
    for j in range(1, len(pedacos)):
        filtro.append(f"{atual}[m{j}]acrossfade=d={fade:g}[mx{j}]")
        atual = f"[mx{j}]"
    filtro.append(f"{atual}anull[musica]")
    return argumentos, ";".join(filtro)
