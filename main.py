import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import re
import time
import subprocess
import platform

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PASTA_VIDEOS = os.path.join(PASTA_SCRIPT, "Vídeos")
PASTA_CORTES = os.path.join(PASTA_SCRIPT, "Cortes")

# Cookies que indicam que a conta está logada no YouTube
COOKIES_LOGIN = ("LOGIN_INFO", "SID", "__Secure-3PSID")

PASSOS_COOKIES = ("Para exportar de novo:\n"
                  "1. Abra uma janela anônima e faça login no YouTube\n"
                  "2. Abra youtube.com/robots.txt\n"
                  "3. Clique na extensão 'Get cookies.txt LOCALLY' → Export\n"
                  "4. Feche a janela anônima\n"
                  f"5. Substitua o arquivo de cookies nesta pasta:\n{PASTA_SCRIPT}")


def achar_cookies():
    """Procura na pasta do script um arquivo terminado em cookies.txt (ex: www.youtube.com_cookies.txt)"""
    for nome in sorted(os.listdir(PASTA_SCRIPT)):
        if nome.lower().endswith("cookies.txt"):
            return os.path.join(PASTA_SCRIPT, nome)
    return None


def cookies_vencidos(caminho):
    """True se os cookies de login do arquivo já expiraram (ou não existem)"""
    expiracoes = []
    with open(caminho, encoding="utf-8", errors="ignore") as f:
        for linha in f:
            campos = linha.rstrip("\n").split("\t")
            if len(campos) == 7 and campos[5] in COOKIES_LOGIN:
                expiracoes.append(int(campos[4] or 0))
    # Expiração 0 = cookie de sessão, que não vence pela data
    return not expiracoes or any(0 < exp < time.time() for exp in expiracoes)


def firefox_instalado():
    return os.path.isdir(os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles"))


def para_segundos(texto):
    """Converte '31:31', '31,31', '1:02:05' ou '90' em segundos"""
    partes = re.split(r'[:,.]', texto.strip())
    segundos = 0
    for parte in partes:
        segundos = segundos * 60 + int(parte)
    return segundos


def formatar_tempo(segundos):
    """Converte segundos em '31m31s' (ou '1h02m05s')"""
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def nome_de_arquivo(texto):
    """Remove caracteres que o Windows não aceita em nomes de arquivo"""
    texto = re.sub(r'[/\\|]', '-', texto)
    return re.sub(r'[<>:"?*\x00-\x1f]', '', texto).strip(" .")[:100]


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Downloader Pro (1080p/720p)")
        self.root.geometry("540x680")
        self.root.configure(padx=20, pady=15)
        self.video_atual = None  # vídeo usado para gerar os cortes

        # --- 1) BAIXAR VÍDEO ---
        tk.Label(root, text="1) URL do Vídeo (Prioridade 1080p):", font=("Arial", 10, "bold")).pack()

        self.url_entry = tk.Entry(root, width=55)
        self.url_entry.pack(pady=8)

        self.btn_download = tk.Button(root, text="BAIXAR VÍDEO", command=self.start_download_thread,
                                      bg="#c4302b", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_download.pack(pady=5, fill=tk.X)

        self.progress_label = tk.Label(root, text="Aguardando link...")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=5)

        self.status_label = tk.Label(root, text="", font=("Arial", 8), fg="gray", wraplength=480)
        self.status_label.pack()
        self.mostrar_status_cookies()

        ttk.Separator(root, orient="horizontal").pack(fill=tk.X, pady=12)

        # --- 2) GERAR CORTES ---
        tk.Label(root, text="2) Gerar cortes", font=("Arial", 10, "bold")).pack()

        self.video_label = tk.Label(root, text="Nenhum vídeo selecionado", font=("Arial", 8), fg="gray",
                                    wraplength=480)
        self.video_label.pack(pady=(4, 2))
        tk.Button(root, text="Escolher outro vídeo do PC...", command=self.escolher_video).pack()

        # Cabeçalho da lista de cortes
        cabecalho = tk.Frame(root)
        cabecalho.pack(fill=tk.X, pady=(10, 0))
        self.configurar_colunas(cabecalho)
        for coluna, texto in enumerate(("Início", "Fim", "Nome do corte (opcional)")):
            tk.Label(cabecalho, text=texto, font=("Arial", 8, "bold")).grid(row=0, column=coluna, sticky="w")

        # Lista de cortes com rolagem (uma linha por corte)
        container = tk.Frame(root)
        container.pack(fill=tk.X)
        canvas = tk.Canvas(container, height=150, highlightthickness=0)
        rolagem = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.lista_frame = tk.Frame(canvas)
        self.lista_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.lista_frame, anchor="nw")
        canvas.configure(yscrollcommand=rolagem.set)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        rolagem.pack(side=tk.RIGHT, fill=tk.Y)
        # Rolagem com a roda do mouse só enquanto o mouse está sobre a lista
        rolar = lambda e: canvas.yview_scroll(int(-e.delta / 120), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", rolar))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        self.canvas_cortes = canvas

        self.linhas = []
        self.adicionar_linha()
        tk.Button(root, text="+ Adicionar corte", command=self.adicionar_linha).pack(anchor="w", pady=(4, 6))
        tk.Label(root, text="Tempos em minutos:segundos (ex: 15:05)  •  Enter no nome adiciona outro corte",
                 font=("Arial", 8), fg="gray").pack()

        opcoes = tk.Frame(root)
        opcoes.pack()
        self.whatsapp_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opcoes, text="Caber no WhatsApp (até 180 MB)", variable=self.whatsapp_var).pack(side=tk.LEFT, padx=8)
        self.volume_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opcoes, text="Equilibrar volume do áudio", variable=self.volume_var).pack(side=tk.LEFT, padx=8)

        self.btn_corte = tk.Button(root, text="GERAR CORTES", command=self.start_corte_thread, state="disabled",
                                   bg="#2b6cc4", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_corte.pack(pady=6, fill=tk.X)

        self.corte_label = tk.Label(root, text="", font=("Arial", 8), wraplength=480)
        self.corte_label.pack()

        self.corte_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.corte_bar.pack(pady=5)

    @staticmethod
    def configurar_colunas(frame):
        """Mesma largura de colunas no cabeçalho e nas linhas, para ficarem alinhados"""
        for coluna, largura in enumerate((75, 75, 300, 30)):
            frame.columnconfigure(coluna, minsize=largura)

    def adicionar_linha(self):
        linha = tk.Frame(self.lista_frame)
        linha.pack(fill=tk.X, pady=2)
        self.configurar_colunas(linha)
        inicio = tk.Entry(linha, width=8, justify="center")
        fim = tk.Entry(linha, width=8, justify="center")
        nome = tk.Entry(linha, width=40)
        inicio.grid(row=0, column=0, sticky="w")
        fim.grid(row=0, column=1, sticky="w")
        nome.grid(row=0, column=2, sticky="w")
        tk.Button(linha, text="✕", fg="#c4302b", relief="flat",
                  command=lambda: self.remover_linha(linha)).grid(row=0, column=3)
        nome.bind("<Return>", lambda e: self.adicionar_linha())

        self.linhas.append({"frame": linha, "inicio": inicio, "fim": fim, "nome": nome})
        inicio.focus_set()
        # Rola a lista até a linha nova
        self.root.after(50, lambda: self.canvas_cortes.yview_moveto(1.0))

    def remover_linha(self, linha):
        if len(self.linhas) == 1:
            # Sempre fica pelo menos uma linha: só limpa os campos
            for campo in ("inicio", "fim", "nome"):
                self.linhas[0][campo].delete(0, tk.END)
            return
        self.linhas = [l for l in self.linhas if l["frame"] is not linha]
        linha.destroy()

    def ler_cortes(self):
        """Lê os cortes da tela. Retorna (cortes, erros)"""
        cortes, erros = [], []
        for n, linha in enumerate(self.linhas, start=1):
            inicio_txt = linha["inicio"].get().strip()
            fim_txt = linha["fim"].get().strip()
            nome = nome_de_arquivo(linha["nome"].get())
            if not (inicio_txt or fim_txt or nome):
                continue  # linha vazia
            try:
                inicio, fim = para_segundos(inicio_txt), para_segundos(fim_txt)
            except ValueError:
                erros.append(f"Corte {n}: preencha início e fim como minutos:segundos (ex: 15:05)")
                continue
            if fim <= inicio:
                erros.append(f"Corte {n}: o fim ({formatar_tempo(fim)}) precisa ser depois do início ({formatar_tempo(inicio)})")
                continue
            cortes.append((inicio, fim, nome))
        return cortes, erros

    def na_tela(self, funcao, *args, **kwargs):
        """Executa uma atualização da interface na thread principal (o tkinter não é thread-safe)"""
        self.root.after(0, lambda: funcao(*args, **kwargs))

    def mostrar_status_cookies(self):
        arquivo = achar_cookies()
        if arquivo and cookies_vencidos(arquivo):
            self.status_label.config(text="⚠ Seus cookies do YouTube venceram — exporte de novo", fg="#c47a00")
        elif arquivo:
            self.status_label.config(text="cookies.txt encontrado ✓", fg="gray")
        elif firefox_instalado():
            self.status_label.config(text="Usando cookies do Firefox", fg="gray")
        else:
            self.status_label.config(text="Sem cookies (o YouTube pode bloquear)", fg="gray")

    def selecionar_video(self, caminho):
        self.video_atual = caminho
        self.video_label.config(text=f"Vídeo: {os.path.basename(caminho)}", fg="black")
        self.btn_corte.config(state="normal")

    def escolher_video(self):
        caminho = filedialog.askopenfilename(
            title="Escolha o vídeo para cortar",
            initialdir=PASTA_VIDEOS if os.path.isdir(PASTA_VIDEOS) else PASTA_SCRIPT,
            filetypes=[("Vídeos", "*.mp4 *.mkv *.webm *.mov"), ("Todos os arquivos", "*.*")])
        if caminho:
            self.selecionar_video(os.path.normpath(caminho))

    def rodar_ytdlp(self, url, paralelos, arquivo_cookies):
        """Baixa com o yt-dlp num processo separado. Retorna (caminho_final, erro, avisos).

        Processo separado porque, quando o download falha no meio, o yt-dlp pode deixar arquivos
        abertos; ao fim do processo o Windows libera tudo e a próxima tentativa continua de onde parou.
        """
        comando = [
            sys.executable, "-m", "yt_dlp", "--newline", "--no-colors", "--progress",
            # Prefere H.264 (avc1), que abre em qualquer player; senão o melhor MP4 até 1080p.
            "-f", ("bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
                   "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"),
            "--merge-output-format", "mp4",
            "-o", os.path.join(PASTA_VIDEOS, "%(title)s.%(ext)s"),
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
            errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        caminho, erros, avisos = None, [], []
        for linha in processo.stdout:
            linha = linha.strip()
            if linha.startswith("PROGRESSO"):
                try:
                    percent = float(linha.split()[-1].rstrip("%"))
                    self.na_tela(self.progress_bar.config, value=percent)
                    self.na_tela(self.progress_label.config,
                                 text="Mesclando áudio e vídeo..." if percent >= 100 else f"Baixando: {percent}%")
                except ValueError:
                    pass
            elif linha.startswith("ARQUIVO "):
                caminho = linha[len("ARQUIVO "):]
            elif linha.startswith("ERROR:"):
                erros.append(linha)
            elif linha.startswith("WARNING:"):
                avisos.append(linha)
        processo.wait()
        erro = None if processo.returncode == 0 and caminho else ("\n".join(erros) or "O download falhou sem mensagem de erro")
        return caminho, erro, avisos

    @staticmethod
    def limpar_temporarios(caminho_video):
        """Apaga pedaços que sobraram de uma tentativa que falhou (ex: 'Aula.f140.m4a.part-Frag12')"""
        pasta = os.path.dirname(caminho_video)
        titulo = os.path.splitext(os.path.basename(caminho_video))[0]
        for nome in os.listdir(pasta):
            if nome.startswith(titulo + ".") and (".part" in nome or nome.endswith(".ytdl")):
                try:
                    os.remove(os.path.join(pasta, nome))
                except OSError:
                    pass

    def download_video(self):
        url = self.url_entry.get().strip()
        if not url:
            self.na_tela(messagebox.showwarning, "Aviso", "Por favor, cole um link!")
            return

        self.na_tela(self.btn_download.config, state="disabled")
        os.makedirs(PASTA_VIDEOS, exist_ok=True)
        arquivo_cookies = achar_cookies()

        try:
            # Se o vídeo já foi baixado antes, o yt-dlp reaproveita o arquivo
            caminho, erro, avisos = self.rodar_ytdlp(url, 8, arquivo_cookies)
            if erro and "not a bot" not in erro and "live event" not in erro:
                # Pedaços quebrados no YouTube travam o download em paralelo; um por vez, o
                # yt-dlp pula esses pedaços. Continua de onde parou, sem baixar tudo de novo.
                self.na_tela(self.progress_label.config, text="Tentando de novo em modo seguro (mais lento)...")
                caminho, erro, avisos = self.rodar_ytdlp(url, 1, arquivo_cookies)
            if erro:
                raise RuntimeError(erro)
            self.limpar_temporarios(caminho)
            self.na_tela(self.selecionar_video, caminho)

            self.na_tela(self.progress_label.config, text="Pronto! Agora você pode gerar cortes abaixo.")
            self.na_tela(self.status_label.config, text="Concluído com sucesso!", fg="green")
            if any("no longer valid" in aviso for aviso in avisos):
                self.na_tela(self.status_label.config, fg="#c47a00",
                             text="Baixou, mas seus cookies não valem mais — exporte de novo antes que o YouTube bloqueie")
            titulo = os.path.splitext(os.path.basename(caminho))[0]
            self.na_tela(messagebox.showinfo, "Sucesso", f"Vídeo baixado:\n{titulo}")

        except Exception as e:
            erro = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            if "live event" in erro:
                dica = ("Esse link é de uma live que acabou de terminar.\n"
                        "O YouTube ainda está processando o vídeo; tente de novo mais tarde.")
            elif "timed out" in erro.lower() or "connection" in erro.lower():
                dica = ("A conexão com o YouTube travou.\n"
                        "Clique em BAIXAR VÍDEO de novo: o download continua de onde parou.")
            elif "No video formats" in erro or "reloaded" in erro:
                dica = 'Atualize o yt-dlp: python -m pip install -U "yt-dlp[default]"'
            elif ("not a bot" in erro or "429" in erro) and arquivo_cookies:
                dica = "Seus cookies do YouTube venceram ou foram invalidados.\n\n" + PASSOS_COOKIES
            elif "not a bot" in erro or "429" in erro:
                dica = ("O YouTube bloqueou o acesso sem login.\n\n"
                        "Faça login no YouTube pelo Firefox e tente de novo,\n"
                        "ou salve um cookies.txt do YouTube nesta pasta:\n"
                        f"{PASTA_SCRIPT}")
            else:
                dica = "Verifique se o FFmpeg está instalado."
            self.na_tela(messagebox.showerror, "Erro", f"Ocorreu um problema: {erro}\n\n{dica}")
            self.na_tela(self.status_label.config, text="Erro no processo", fg="red")
        finally:
            self.na_tela(self.btn_download.config, state="normal")
            self.na_tela(self.progress_bar.config, value=0)

    def fazer_cortes(self, cortes, limitar_whatsapp, equilibrar_volume):
        video = self.video_atual
        pasta = os.path.join(PASTA_CORTES, os.path.splitext(os.path.basename(video))[0])
        os.makedirs(pasta, exist_ok=True)

        self.na_tela(self.btn_corte.config, state="disabled")
        gerados, usados = [], set()
        try:
            for i, (inicio, fim, nome) in enumerate(cortes):
                nome = nome or f"corte {formatar_tempo(inicio)} a {formatar_tempo(fim)}"
                # Dois cortes com o mesmo nome na lista: numera o segundo
                final, n = nome, 2
                while final.lower() in usados:
                    final, n = f"{nome} ({n})", n + 1
                usados.add(final.lower())

                def progresso(fracao, i=i, final=final):
                    total = (i + fracao) / len(cortes) * 100
                    self.na_tela(self.corte_bar.config, value=total)
                    self.na_tela(self.corte_label.config, fg="black",
                                 text=f"Corte {i + 1} de {len(cortes)} — {final} ({fracao * 100:.0f}%)")

                caminho = os.path.join(pasta, final + ".mp4")
                self.gerar_corte(video, inicio, fim, caminho, limitar_whatsapp=limitar_whatsapp,
                                 equilibrar_volume=equilibrar_volume, progresso=progresso)
                gerados.append(final)

            self.na_tela(self.corte_label.config, fg="green",
                         text=f"✓ {len(gerados)} corte(s) gerado(s) em Cortes\\{os.path.basename(pasta)}")
            self.abrir_pasta_arquivo(pasta)
        except Exception as e:
            self.na_tela(self.corte_label.config, fg="red",
                         text=f"Erro no corte {len(gerados) + 1} — {len(gerados)} gerado(s) antes do erro")
            self.na_tela(messagebox.showerror, "Erro", str(e))
        finally:
            self.na_tela(self.btn_corte.config, state="normal")
            self.na_tela(self.corte_bar.config, value=0)

    def gerar_corte(self, caminho_video, inicio, fim, caminho_corte, limitar_whatsapp=False,
                    equilibrar_volume=False, progresso=None):
        """Corta o trecho [inicio, fim] do vídeo com o ffmpeg, reprocessando para o corte ficar exato"""
        duracao = fim - inicio
        # CRF 23 mantém a qualidade do vídeo do YouTube sem inflar o tamanho
        video_opts = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
        if limitar_whatsapp:
            # Teto de bitrate para o arquivo ficar abaixo de ~170 MB (limite do WhatsApp é 180 MB)
            audio_kbps = 128
            video_kbps = max(int(170 * 8 * 1024 / duracao) - audio_kbps, 150)
            video_opts += ["-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps * 2}k"]
        audio_opts = []
        if equilibrar_volume:
            # loudnorm: deixa o volume no padrão de redes sociais (-16 LUFS) e aproxima
            # partes baixas (fala) das altas (berimbau/palmas). -ar porque o loudnorm sobe para 192 kHz.
            audio_opts = ["-af", "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000"]
        comando = [
            "ffmpeg", "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
            "-ss", str(inicio), "-i", caminho_video, "-t", str(duracao),
            *video_opts, *audio_opts,
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            caminho_corte,
        ]
        processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # O ffmpeg informa o tempo já processado em linhas "out_time_us=..."
        for linha in processo.stdout:
            if progresso and linha.startswith(("out_time_us=", "out_time_ms=")):
                try:
                    feito = int(linha.split("=")[1]) / 1_000_000
                    progresso(min(feito / duracao, 1.0))
                except ValueError:
                    pass
        erro = processo.stderr.read()
        if processo.wait() != 0:
            raise RuntimeError(f"ffmpeg falhou ao cortar: {erro.strip()}")
        return caminho_corte

    def start_download_thread(self):
        threading.Thread(target=self.download_video, daemon=True).start()

    def start_corte_thread(self):
        cortes, erros = self.ler_cortes()
        if erros:
            messagebox.showwarning("Aviso", "Corrija os cortes:\n\n" + "\n".join(erros))
            return
        if not cortes:
            messagebox.showwarning("Aviso", "Preencha pelo menos um corte (início e fim), ex: 15:05 e 16:20")
            return
        threading.Thread(target=self.fazer_cortes, args=(cortes, self.whatsapp_var.get(), self.volume_var.get()),
                         daemon=True).start()

    def abrir_pasta_arquivo(self, path=PASTA_SCRIPT):
        """Abre a pasta indicada (por padrão a do script)"""
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin": # macOS
            os.system(f'open "{path}"')
        else: # Linux
            os.system(f'xdg-open "{path}"')

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
