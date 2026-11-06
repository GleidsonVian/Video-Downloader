"""Junta vários trechos (de um vídeo ou de arquivos já prontos) num vídeo só, com transição, vinhetas e música."""
import os
import subprocess

from .config import EXT_IMAGEM
from .cortes import LOUDNORM, filtro_audio, info_midia, opcoes_de_video, rodar_ffmpeg

# Nome mostrado na tela -> duração da transição entre os trechos, em segundos
TRANSICOES = {"Corte seco": 0.0, "Fade suave (0,5 s)": 0.5, "Fade longo (1 s)": 1.0}
SILENCIO = "anullsrc=r=48000:cl=stereo"  # áudio mudo para imagens e vídeos sem som


def eh_imagem(caminho):
    return caminho.lower().endswith(EXT_IMAGEM)


def cor_de_fundo(imagem):
    """Cor do canto da imagem ('0xRRGGBB'), usada para preencher as laterais quando a imagem não tem a
    mesma proporção do vídeo (um logo quadrado de fundo branco não pode ficar entre faixas pretas)"""
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", imagem, "-vf", "crop=1:1:0:0,format=rgb24",
                            "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if len(r.stdout) >= 3:
            return "0x%02x%02x%02x" % tuple(r.stdout[:3])
    except (OSError, subprocess.SubprocessError):
        pass
    return "black"


def montar_filtro(duracoes, transicao, modo_audio="original", equilibrar_volume=False, volume_musica=30,
                  tamanho=None, entradas=None, entrada_musica=None, fundos=None):
    """Monta o filtro do ffmpeg para emendar os trechos. Retorna (filtro, duração_total_em_segundos).

    'entradas' diz, para cada trecho, o par (índice da entrada de vídeo, índice da entrada de áudio) no
    ffmpeg; por padrão o trecho i usa a entrada i para os dois. 'entrada_musica' é o índice da música
    (por padrão, a entrada logo depois dos trechos). As saídas são [vjunto] (vídeo) e [aout] (áudio).
    'tamanho' (largura, altura) ajusta trechos de tamanhos diferentes ao mesmo quadro, com faixas pretas
    se a proporção for outra (cortes de aulas diferentes podem ter resoluções diferentes).
    'fundos' dá a cor dessas faixas em cada trecho (padrão: preto).
    """
    n = len(duracoes)
    entradas = entradas or [(i, i) for i in range(n)]
    if entrada_musica is None:
        entrada_musica = n
    # A transição não pode ser maior que a metade do trecho mais curto
    fade = min(transicao, min(duracoes) / 2) if n > 1 else 0
    fundos = fundos or ["black"] * n
    filtro = []
    for i, (entrada_video, entrada_audio) in enumerate(entradas):
        ajuste = ""
        if tamanho:
            w, h = tamanho
            ajuste = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                      f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={fundos[i]},")
        # Mesmo formato em todos os trechos: o xfade e o concat exigem
        filtro.append(f"[{entrada_video}:v]settb=AVTB,setpts=PTS-STARTPTS,{ajuste}fps=30,format=yuv420p,setsar=1[v{i}]")
        filtro.append(f"[{entrada_audio}:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[a{i}]")

    if fade <= 0:  # corte seco
        filtro.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vjunto][ajunto]")
        total = sum(duracoes)
    else:  # cada trecho começa a se fundir com o anterior 'fade' segundos antes dele acabar
        video, audio, total = "[v0]", "[a0]", duracoes[0]
        for i in range(1, n):
            filtro.append(f"{video}[v{i}]xfade=transition=fade:duration={fade:g}:offset={total - fade:g}[vx{i}]")
            filtro.append(f"{audio}[a{i}]acrossfade=d={fade:g}[ax{i}]")
            video, audio, total = f"[vx{i}]", f"[ax{i}]", total + duracoes[i] - fade
        filtro.append(f"{video}null[vjunto]")
        filtro.append(f"{audio}anull[ajunto]")

    if modo_audio == "original":
        filtro.append(f"[ajunto]{LOUDNORM if equilibrar_volume else 'anull'}[aout]")
    else:  # a música cobre o vídeo todo, de ponta a ponta
        filtro.append(filtro_audio(modo_audio, equilibrar_volume, volume_musica, total,
                                   voz="[ajunto]", entrada_musica=f"[{entrada_musica}:a]"))
        if modo_audio == "musica":
            filtro.append("[ajunto]anullsink")  # só a música: o áudio original é descartado
    return ";".join(filtro), total


def montar_entradas(trechos):
    """Argumentos de entrada do ffmpeg para os trechos [(caminho, início, fim)].

    Retorna (argumentos, [(entrada de vídeo, entrada de áudio) de cada trecho], próxima entrada livre).
    Imagens ficam na tela pelo tempo pedido; o que não tem áudio ganha silêncio.
    """
    argumentos, pares, indice, tem_audio = [], [], 0, {}
    for caminho, inicio, fim in trechos:
        duracao = fim - inicio
        if eh_imagem(caminho):
            argumentos += ["-loop", "1", "-framerate", "30", "-t", str(duracao), "-i", caminho]
            com_audio = False
        else:
            argumentos += ["-ss", str(inicio), "-t", str(duracao), "-i", caminho]
            if caminho not in tem_audio:
                tem_audio[caminho] = info_midia(caminho)["audio"]
            com_audio = tem_audio[caminho]
        entrada_video, indice = indice, indice + 1
        if com_audio:
            pares.append((entrada_video, entrada_video))
        else:
            argumentos += ["-f", "lavfi", "-t", str(duracao), "-i", SILENCIO]
            pares.append((entrada_video, indice))
            indice += 1
    return argumentos, pares, indice


def trechos_de_arquivos(caminhos):
    """Transforma arquivos já prontos em trechos [(caminho, 0, duração)], para juntar o arquivo inteiro.

    Levanta RuntimeError se algum arquivo sumiu ou não pôde ser lido.
    """
    trechos = []
    for caminho in caminhos:
        if not os.path.exists(caminho):
            raise RuntimeError(f"O arquivo não existe mais:\n{caminho}")
        duracao = info_midia(caminho)["duracao"]
        if duracao <= 0:
            raise RuntimeError(f"Não consegui ler este vídeo:\n{os.path.basename(caminho)}")
        trechos.append((caminho, 0, round(duracao, 2)))
    return trechos


def trecho_de_vinheta(caminho, duracao_imagem):
    """Vinheta (vídeo ou imagem) como trecho. A imagem dura 'duracao_imagem' segundos."""
    if eh_imagem(caminho):
        if not os.path.exists(caminho):
            raise RuntimeError(f"A imagem da vinheta não existe mais:\n{caminho}")
        return (caminho, 0, duracao_imagem)
    return trechos_de_arquivos([caminho])[0]


def juntar_cortes(trechos, caminho_saida, transicao=0.0, limitar_whatsapp=False,
                  equilibrar_volume=False, usar_gpu=False, modo_audio="original", musica=None,
                  volume_musica=30, inicio_musica=0, abertura=None, encerramento=None, duracao_imagem=3.0,
                  ao_progresso=None, ao_iniciar=None):
    """Junta os 'trechos' [(caminho, início, fim), ...], na ordem dada, num único arquivo.

    Os trechos podem ser partes de um mesmo vídeo ou arquivos diferentes (cortes já prontos).
    'abertura' e 'encerramento' (vídeo ou imagem) entram antes e depois de todos os trechos.
    Tudo numa passada só do ffmpeg: o vídeo é recodificado uma vez (sem perder qualidade por emendas).
    """
    if modo_audio != "original" and (not musica or not os.path.exists(musica)):
        raise RuntimeError("Escolha uma música em \"Áudio do corte\" (ou use o áudio original).")
    principal = info_midia(trechos[0][0])  # o tamanho do vídeo final é o do primeiro CORTE, não o da vinheta
    tamanho = (principal["largura"], principal["altura"]) if principal["largura"] else None
    todos = list(trechos)
    if abertura:
        todos.insert(0, trecho_de_vinheta(abertura, duracao_imagem))
    if encerramento:
        todos.append(trecho_de_vinheta(encerramento, duracao_imagem))

    argumentos, pares, proxima = montar_entradas(todos)
    duracoes = [fim - inicio for _, inicio, fim in todos]
    fundos = [cor_de_fundo(c) if eh_imagem(c) else "black" for c, _, _ in todos]
    filtro, total = montar_filtro(duracoes, transicao, modo_audio, equilibrar_volume, volume_musica, tamanho,
                                  pares, proxima, fundos)
    if modo_audio != "original":
        argumentos += ["-stream_loop", "-1", "-ss", str(inicio_musica), "-i", musica]  # recomeça se acabar
    comando = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1", *argumentos,
        "-filter_complex", filtro, "-map", "[vjunto]", "-map", "[aout]", "-t", f"{total:g}",
        *opcoes_de_video(trechos[0][0], total, limitar_whatsapp, usar_gpu),
        "-ar", "48000", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", caminho_saida,
    ]
    rodar_ffmpeg(comando, total, ao_progresso, ao_iniciar)
    return caminho_saida
