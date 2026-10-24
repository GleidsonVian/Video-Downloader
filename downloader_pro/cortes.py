"""Geração dos cortes com o ffmpeg (sem nada de interface)."""
import os
import subprocess

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=7"  # volume padrão de redes sociais (-16 LUFS)


def filtro_audio(modo, equilibrar_volume, volume_musica, duracao):
    """Monta o filtro do ffmpeg que combina o áudio do vídeo ([0:a]) com a música ([1:a]) em [aout]"""
    fade = min(2.0, duracao / 4)  # a música entra e sai suavemente, sem corte seco
    musica = f"[1:a]afade=t=in:d={fade:g},afade=t=out:st={max(duracao - fade, 0):g}:d={fade:g}"
    normalizar = f",{LOUDNORM}" if equilibrar_volume else ""
    if modo == "musica":
        return f"{musica}{normalizar}[aout]"
    # Mistura: a voz do vídeo no volume original e a música no volume escolhido (5 a 100%).
    # normalize=0 mantém os volumes como estão, em vez de abaixar os dois pela metade.
    return (f"{musica},volume={volume_musica / 100:g}[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:normalize=0{normalizar}[aout]")


def placa_amd_disponivel():
    """True se o ffmpeg consegue de fato codificar com a placa AMD (testa um quadro de 0,2 s)"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=0.2",
             "-c:v", "h264_amf", "-f", "null", "-"],
            capture_output=True, timeout=20, creationflags=SEM_JANELA)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def bitrate_video_kbps(caminho):
    """Bitrate do vídeo original em kbps (3000 se o ffprobe não informar)"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=bit_rate",
             "-of", "default=nw=1:nk=1", caminho],
            capture_output=True, text=True, timeout=20, creationflags=SEM_JANELA)
        return max(int(int(r.stdout.strip()) / 1000), 500)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 3000


def opcoes_de_video(caminho_video, duracao, limitar_whatsapp, usar_gpu):
    """Opções de codificação do vídeo: pela placa AMD ou pelo processador (x264)"""
    # Teto de bitrate para o arquivo ficar abaixo de ~170 MB (limite do WhatsApp é 180 MB)
    teto_kbps = max(int(170 * 8 * 1024 / duracao) - 128, 150) if limitar_whatsapp else None
    if usar_gpu:
        # A placa não tem "CRF": mira no bitrate do vídeo original (que já vem comprimido do YouTube)
        alvo_kbps = bitrate_video_kbps(caminho_video)
        if teto_kbps:
            alvo_kbps = min(alvo_kbps, teto_kbps)
        return ["-c:v", "h264_amf", "-quality", "speed", "-rc", "vbr_peak", "-b:v", f"{alvo_kbps}k",
                "-maxrate", f"{teto_kbps or alvo_kbps * 2}k", "-pix_fmt", "yuv420p"]
    # CRF 23 mantém a qualidade do vídeo do YouTube sem inflar o tamanho
    opcoes = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    if teto_kbps:
        opcoes += ["-maxrate", f"{teto_kbps}k", "-bufsize", f"{teto_kbps * 2}k"]
    return opcoes


def gerar_corte(caminho_video, inicio, fim, caminho_corte, limitar_whatsapp=False, equilibrar_volume=False,
                usar_gpu=False, modo_audio="original", musica=None, volume_musica=30, inicio_musica=0,
                ao_progresso=None, ao_iniciar=None):
    """Corta o trecho [inicio, fim] do vídeo com o ffmpeg, reprocessando para o corte ficar exato.

    modo_audio: "original" (áudio do vídeo), "mistura" (áudio do vídeo + música baixinha ao fundo)
    ou "musica" (só a música). A música recomeça sozinha se for mais curta que o corte.
    ao_progresso(fração 0 a 1) acompanha o andamento; ao_iniciar(processo) permite cancelar.
    """
    duracao = fim - inicio
    entrada_musica, audio_opts = [], []
    if modo_audio != "original":
        if not musica or not os.path.exists(musica):
            raise RuntimeError("Escolha uma música em \"Áudio do corte\" (ou use o áudio original).")
        # -stream_loop -1: se a música acabar antes do corte, ela recomeça
        entrada_musica = ["-stream_loop", "-1", "-ss", str(inicio_musica), "-i", musica]
        audio_opts = ["-filter_complex", filtro_audio(modo_audio, equilibrar_volume, volume_musica, duracao),
                      "-map", "0:v", "-map", "[aout]", "-ar", "48000"]
    elif equilibrar_volume:
        # Aproxima partes baixas (fala) das altas (berimbau/palmas).
        # -ar porque o loudnorm sobe para 192 kHz.
        audio_opts = ["-af", LOUDNORM, "-ar", "48000"]
    comando = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
        "-ss", str(inicio), "-i", caminho_video, *entrada_musica, "-t", str(duracao),
        *opcoes_de_video(caminho_video, duracao, limitar_whatsapp, usar_gpu), *audio_opts,
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        caminho_corte,
    ]
    processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                creationflags=SEM_JANELA)
    if ao_iniciar:
        ao_iniciar(processo)
    try:
        # O ffmpeg informa o tempo já processado em linhas "out_time_us=..."
        for linha in processo.stdout:
            if ao_progresso and linha.startswith(("out_time_us=", "out_time_ms=")):
                try:
                    ao_progresso(min(int(linha.split("=")[1]) / 1_000_000 / duracao, 1.0))
                except ValueError:
                    pass
        erro = processo.stderr.read()
        if processo.wait() != 0:
            raise RuntimeError(f"ffmpeg falhou ao cortar: {erro.strip()}")
    finally:
        if ao_iniciar:
            ao_iniciar(None)
    return caminho_corte
