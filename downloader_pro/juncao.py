"""Junta vários trechos do mesmo vídeo num vídeo só, com transição e música de fundo (sem interface)."""
import os

from .cortes import LOUDNORM, filtro_audio, opcoes_de_video, rodar_ffmpeg

# Nome mostrado na tela -> duração da transição entre os trechos, em segundos
TRANSICOES = {"Corte seco": 0.0, "Fade suave (0,5 s)": 0.5, "Fade longo (1 s)": 1.0}


def montar_filtro(duracoes, transicao, modo_audio="original", equilibrar_volume=False, volume_musica=30):
    """Monta o filtro do ffmpeg para emendar os trechos. Retorna (filtro, duração_total_em_segundos).

    Entradas 0..N-1 são os trechos (vídeo e áudio); a entrada N é a música, se houver.
    As saídas são [vjunto] (vídeo) e [aout] (áudio).
    """
    n = len(duracoes)
    # A transição não pode ser maior que a metade do trecho mais curto
    fade = min(transicao, min(duracoes) / 2) if n > 1 else 0
    filtro = []
    for i in range(n):
        # Mesmo formato em todos os trechos: o xfade e o concat exigem
        filtro.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps=30,format=yuv420p,setsar=1[v{i}]")
        filtro.append(f"[{i}:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[a{i}]")

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
                                   voz="[ajunto]", entrada_musica=f"[{n}:a]"))
        if modo_audio == "musica":
            filtro.append("[ajunto]anullsink")  # só a música: o áudio original é descartado
    return ";".join(filtro), total


def juntar_cortes(caminho_video, trechos, caminho_saida, transicao=0.0, limitar_whatsapp=False,
                  equilibrar_volume=False, usar_gpu=False, modo_audio="original", musica=None,
                  volume_musica=30, inicio_musica=0, ao_progresso=None, ao_iniciar=None):
    """Junta os 'trechos' [(início, fim), ...] do vídeo, na ordem dada, num único arquivo.

    Tudo numa passada só do ffmpeg: o vídeo é recodificado uma vez (sem perder qualidade por emendas).
    """
    if modo_audio != "original" and (not musica or not os.path.exists(musica)):
        raise RuntimeError("Escolha uma música em \"Áudio do corte\" (ou use o áudio original).")
    duracoes = [fim - inicio for inicio, fim in trechos]
    filtro, total = montar_filtro(duracoes, transicao, modo_audio, equilibrar_volume, volume_musica)

    entradas = []
    for (inicio, fim), duracao in zip(trechos, duracoes):
        entradas += ["-ss", str(inicio), "-t", str(duracao), "-i", caminho_video]
    if modo_audio != "original":
        entradas += ["-stream_loop", "-1", "-ss", str(inicio_musica), "-i", musica]  # recomeça se acabar
    comando = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1", *entradas,
        "-filter_complex", filtro, "-map", "[vjunto]", "-map", "[aout]", "-t", f"{total:g}",
        *opcoes_de_video(caminho_video, total, limitar_whatsapp, usar_gpu),
        "-ar", "48000", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", caminho_saida,
    ]
    rodar_ffmpeg(comando, total, ao_progresso, ao_iniciar)
    return caminho_saida
