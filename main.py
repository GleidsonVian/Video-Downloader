import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import re
import time
import subprocess
import platform

# No .exe (PyInstaller), __file__ aponta para uma pasta temporária: usa a pasta do próprio .exe
EXECUTAVEL = getattr(sys, "frozen", False)
PASTA_SCRIPT = os.path.dirname(sys.executable if EXECUTAVEL else os.path.abspath(__file__))
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


def tempo_curto(segundos):
    """Converte segundos em '05:49' (ou '1:02:05'), o formato dos campos de início/fim"""
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def carregar_vlc():
    """Importa o python-vlc usando o VLC 64 bits instalado. Retorna o módulo, ou None se não houver VLC"""
    pasta_vlc = os.path.join(os.environ.get("ProgramW6432", r"C:\Program Files"), "VideoLAN", "VLC")
    if os.path.exists(os.path.join(pasta_vlc, "libvlc.dll")):
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", os.path.join(pasta_vlc, "libvlc.dll"))
        os.environ.setdefault("PYTHON_VLC_MODULE_PATH", os.path.join(pasta_vlc, "plugins"))
        os.add_dll_directory(pasta_vlc)
    try:
        import vlc
        return vlc
    except Exception:
        return None


class PlayerCortes:
    """Janela para assistir o vídeo (com velocidade ajustável) e marcar início/fim dos cortes"""

    VELOCIDADES = (1, 1.5, 2, 3, 4)
    FUNDO = "#1e1e1e"

    def __init__(self, app, caminho, vlc):
        self.app = app
        self.vlc = vlc
        self.inicio_marcado = None  # segundos do início do corte em andamento
        self.arrastando = None      # posição (s) enquanto o mouse arrasta a linha do tempo
        self.marcados = 0

        self.janela = tk.Toplevel(app.root)
        self.janela.title(f"Assistir e marcar — {os.path.basename(caminho)}")
        self.janela.geometry("1000x720")
        self.janela.minsize(640, 420)
        self.janela.configure(bg=self.FUNDO)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)

        # Vídeo
        self.tela = tk.Frame(self.janela, bg="black", cursor="hand2")
        self.tela.pack(fill=tk.BOTH, expand=True)
        self.tela.bind("<Button-1>", lambda e: self.play_pause())

        # Linha do tempo: clique ou arraste para ir a qualquer ponto
        self.timeline = tk.Canvas(self.janela, height=36, bg=self.FUNDO, highlightthickness=0, cursor="hand2")
        self.timeline.pack(fill=tk.X, padx=12, pady=(8, 0))
        self.timeline.bind("<Button-1>", self.arrastar)
        self.timeline.bind("<B1-Motion>", self.arrastar)
        self.timeline.bind("<ButtonRelease-1>", self.soltar)

        # Controles
        barra = tk.Frame(self.janela, bg=self.FUNDO)
        barra.pack(fill=tk.X, padx=12, pady=8)
        estilo = dict(bg="#333", fg="white", activebackground="#555", activeforeground="white",
                      relief="flat", font=("Arial", 10, "bold"), padx=8)
        self.btn_play = tk.Button(barra, text="⏸", width=3, command=self.play_pause, **estilo)
        self.btn_play.pack(side=tk.LEFT)
        tk.Button(barra, text="−10s", command=lambda: self.pular(-10), **estilo).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(barra, text="+10s", command=lambda: self.pular(10), **estilo).pack(side=tk.LEFT, padx=(2, 0))
        self.tempo_label = tk.Label(barra, text="00:00 / 00:00", bg=self.FUNDO, fg="white",
                                    font=("Consolas", 12, "bold"))
        self.tempo_label.pack(side=tk.LEFT, padx=14)

        tk.Label(barra, text="Velocidade:", bg=self.FUNDO, fg="#aaa").pack(side=tk.LEFT)
        self.botoes_velocidade = {}
        for v in self.VELOCIDADES:
            b = tk.Button(barra, text=f"{v:g}x", width=4, command=lambda v=v: self.mudar_velocidade(v), **estilo)
            b.pack(side=tk.LEFT, padx=1)
            self.botoes_velocidade[v] = b

        # Botão de marcar numa linha própria, para o texto "FECHAR CORTE (início → agora)" caber inteiro
        barra_marcar = tk.Frame(self.janela, bg=self.FUNDO)
        barra_marcar.pack(pady=(0, 6))
        self.btn_marcar = tk.Button(barra_marcar, command=self.marcar, relief="flat", fg="white",
                                    font=("Arial", 12, "bold"), padx=30, pady=8)
        self.btn_marcar.pack(side=tk.LEFT)
        self.btn_cancelar = tk.Button(barra_marcar, text="Cancelar (Esc)", command=self.cancelar_marcacao, **estilo)

        self.info_label = tk.Label(self.janela, bg=self.FUNDO, fg="#aaa", font=("Arial", 9),
                                   text="Espaço: pausar  •  ← →: 5s  •  ↑ ↓: velocidade  •  M: marcar  •  Esc: cancelar marcação")
        self.info_label.pack(pady=(0, 8))

        for tecla, acao in (("<space>", lambda e: self.play_pause()), ("<Left>", lambda e: self.pular(-5)),
                            ("<Right>", lambda e: self.pular(5)), ("<Up>", lambda e: self.passo_velocidade(1)),
                            ("<Down>", lambda e: self.passo_velocidade(-1)), ("<m>", lambda e: self.marcar()),
                            ("<M>", lambda e: self.marcar()), ("<Escape>", lambda e: self.cancelar_marcacao())):
            self.janela.bind(tecla, acao)

        # VLC desenha o vídeo dentro do frame "tela"
        self.instancia = vlc.Instance("--no-video-title-show", "--quiet")
        self.player = self.instancia.media_player_new()
        self.player.set_media(self.instancia.media_new(caminho))
        self.janela.update_idletasks()
        self.player.set_hwnd(self.tela.winfo_id())
        # Cliques e teclas ficam com o tkinter, não com o VLC
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)
        self.player.play()
        self.velocidade = 1
        self.mudar_velocidade(1)
        self.atualizar_botao_marcar()
        self.janela.focus_force()
        self.atualizar()

    # --- Reprodução ---
    def atual(self):
        return max(self.player.get_time(), 0) / 1000

    def duracao(self):
        return max(self.player.get_length(), 0) / 1000

    def ir_para(self, segundos):
        segundos = min(max(segundos, 0), max(self.duracao() - 0.5, 0))
        if self.player.get_state() == self.vlc.State.Ended:
            # Depois que o vídeo termina, o VLC precisa recomeçar antes de aceitar um novo tempo
            self.player.stop()
            self.player.play()
            self.janela.after(300, lambda: self.player.set_time(int(segundos * 1000)))
        else:
            self.player.set_time(int(segundos * 1000))

    def play_pause(self):
        if self.player.get_state() == self.vlc.State.Ended:
            self.ir_para(0)
        elif self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def pular(self, segundos):
        self.ir_para(self.atual() + segundos)

    def mudar_velocidade(self, v):
        self.velocidade = v
        self.player.set_rate(v)
        for valor, botao in self.botoes_velocidade.items():
            botao.config(bg="#2b6cc4" if valor == v else "#333")

    def passo_velocidade(self, direcao):
        i = self.VELOCIDADES.index(self.velocidade) + direcao
        self.mudar_velocidade(self.VELOCIDADES[min(max(i, 0), len(self.VELOCIDADES) - 1)])

    # --- Linha do tempo ---
    def x_para_segundos(self, x):
        largura = max(self.timeline.winfo_width() - 16, 1)
        return min(max((x - 8) / largura, 0), 1) * self.duracao()

    def segundos_para_x(self, s):
        largura = max(self.timeline.winfo_width() - 16, 1)
        return 8 + (s / self.duracao() if self.duracao() else 0) * largura

    def arrastar(self, evento):
        self.arrastando = self.x_para_segundos(evento.x)
        self.desenhar()

    def soltar(self, evento):
        self.ir_para(self.x_para_segundos(evento.x))
        self.arrastando = None

    def desenhar(self):
        c = self.timeline
        c.delete("all")
        w = c.winfo_width()
        agora = self.arrastando if self.arrastando is not None else self.atual()
        c.create_rectangle(8, 14, w - 8, 22, fill="#444", width=0)
        c.create_rectangle(8, 14, self.segundos_para_x(agora), 22, fill="#c4302b", width=0)
        # Cortes que já estão na lista da janela principal
        for inicio, fim, _ in self.app.ler_cortes()[0]:
            c.create_rectangle(self.segundos_para_x(inicio), 10, self.segundos_para_x(fim), 26,
                               fill="#2b6cc4", width=0)
        # Corte em andamento (início marcado, falta o fim)
        if self.inicio_marcado is not None:
            x0, x1 = sorted((self.segundos_para_x(self.inicio_marcado), self.segundos_para_x(agora)))
            c.create_rectangle(x0, 10, x1, 26, fill="#e69500", width=0)
        x = self.segundos_para_x(agora)
        c.create_oval(x - 7, 11, x + 7, 25, fill="white", outline="")

    def atualizar(self):
        if not self.janela.winfo_exists():
            return
        agora = self.arrastando if self.arrastando is not None else self.atual()
        self.tempo_label.config(text=f"{tempo_curto(agora)} / {tempo_curto(self.duracao())}")
        self.btn_play.config(text="⏸" if self.player.is_playing() else "▶")
        if self.inicio_marcado is not None:
            self.btn_marcar.config(text=f"⏹ FECHAR CORTE  ({tempo_curto(self.inicio_marcado)} → {tempo_curto(agora)})")
        self.desenhar()
        self.janela.after(200, self.atualizar)

    # --- Marcação ---
    def marcar(self):
        agora = self.atual()
        if self.inicio_marcado is None:
            self.inicio_marcado = agora
        else:
            inicio, fim = sorted((self.inicio_marcado, agora))
            if fim - inicio < 1:
                messagebox.showwarning("Aviso", "O corte precisa ter pelo menos 1 segundo.", parent=self.janela)
                return
            # Arredonda para fora, para o corte não perder o começo nem o fim do movimento
            self.app.adicionar_corte(int(inicio), int(fim) + (fim % 1 > 0))
            self.inicio_marcado = None
            self.marcados += 1
            self.info_label.config(fg="#7bd389", text=f"✓ {self.marcados} corte(s) marcado(s) nesta sessão — "
                                   "dê nome a eles e clique em GERAR CORTES na janela principal")
        self.atualizar_botao_marcar()

    def cancelar_marcacao(self):
        self.inicio_marcado = None
        self.atualizar_botao_marcar()

    def atualizar_botao_marcar(self):
        if self.inicio_marcado is None:
            self.btn_marcar.config(text="⏺ MARCAR INÍCIO", bg="#2b6cc4", activebackground="#2b6cc4")
            self.btn_cancelar.pack_forget()
        else:
            self.btn_marcar.config(bg="#c4302b", activebackground="#c4302b")
            self.btn_cancelar.pack(side=tk.LEFT, padx=8, ipady=6)

    def fechar(self):
        self.player.stop()
        self.player.release()
        self.instancia.release()
        self.janela.destroy()


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
        # No .exe o ícone vem empacotado (sys._MEIPASS); rodando pelo Python, fica ao lado do main.py
        icone = os.path.join(getattr(sys, "_MEIPASS", PASTA_SCRIPT), "icone.ico")
        if os.path.exists(icone):
            self.root.iconbitmap(icone)
        self.video_atual = None  # vídeo usado para gerar os cortes
        self.processo_ytdlp = None
        self.processo_corte = None
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

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
        botoes_video = tk.Frame(root)
        botoes_video.pack()
        self.btn_assistir = tk.Button(botoes_video, text="▶ ASSISTIR E MARCAR CORTES", command=self.abrir_player,
                                      state="disabled", bg="#2b6cc4", fg="white", font=("Arial", 9, "bold"))
        self.btn_assistir.pack(side=tk.LEFT, padx=4)
        tk.Button(botoes_video, text="Escolher outro vídeo do PC...", command=self.escolher_video).pack(side=tk.LEFT, padx=4)
        self.player = None

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

    def adicionar_linha(self, focar=True):
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
        if focar:
            inicio.focus_set()
        # Rola a lista até a linha nova
        self.root.after(50, lambda: self.canvas_cortes.yview_moveto(1.0))
        return self.linhas[-1]

    def adicionar_corte(self, inicio, fim):
        """Coloca um corte marcado no player na lista (usa a primeira linha vazia, se houver)"""
        vazia = next((l for l in self.linhas
                      if not any(l[campo].get().strip() for campo in ("inicio", "fim", "nome"))), None)
        # focar=False: não tira o foco do player, senão os atalhos de teclado param de funcionar
        linha = vazia or self.adicionar_linha(focar=False)
        linha["inicio"].insert(0, tempo_curto(inicio))
        linha["fim"].insert(0, tempo_curto(fim))
        self.root.after(50, lambda: self.canvas_cortes.yview_moveto(1.0))

    def abrir_player(self):
        vlc = carregar_vlc()
        if vlc is None:
            messagebox.showerror("VLC não encontrado",
                                 "Para assistir e marcar os cortes, instale o VLC de 64 bits:\n\n"
                                 "winget install VideoLAN.VLC\n\nou baixe em videolan.org")
            return
        # Só um player por vez
        if self.player and self.player.janela.winfo_exists():
            self.player.fechar()
        self.player = PlayerCortes(self, self.video_atual, vlc)

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

    def ao_fechar(self):
        for proc in (self.processo_ytdlp, self.processo_corte):
            if proc and proc.poll() is None:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        self.root.destroy()

    def selecionar_video(self, caminho):
        self.video_atual = caminho
        self.video_label.config(text=f"Vídeo: {os.path.basename(caminho)}", fg="black")
        self.btn_corte.config(state="normal")
        self.btn_assistir.config(state="normal")

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
        # No .exe não há Python separado: o próprio .exe roda o yt-dlp (veja o fim do arquivo)
        rodar = [sys.executable, "--ytdlp"] if EXECUTAVEL else [sys.executable, "-m", "yt_dlp"]
        comando = [
            *rodar, "--newline", "--no-colors", "--progress",
            # Prefere H.264 (avc1), que abre em qualquer player; senão o melhor MP4 até 1080p.
            "-f", ("bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
                   "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"),
            "--merge-output-format", "mp4",
            # Evita o segundo passe lento do +faststart no Windows que costuma travar com antivírus/explorer
            "--postprocessor-args", "Merger:-movflags 0",
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
        self.processo_ytdlp = processo
        caminho, erros, avisos = None, [], []
        try:
            for linha in processo.stdout:
                linha = linha.strip()
                if linha.startswith("PROGRESSO"):
                    try:
                        percent = float(linha.split()[-1].rstrip("%"))
                        self.na_tela(self.progress_bar.config, value=percent)
                        self.na_tela(self.progress_label.config,
                                     text="Mesclando áudio e vídeo (quase pronto)..." if percent >= 100 else f"Baixando: {percent}%")
                    except ValueError:
                        pass
                elif linha.startswith("ARQUIVO "):
                    caminho = linha[len("ARQUIVO "):]
                elif linha.startswith("ERROR:"):
                    erros.append(linha)
                elif linha.startswith("WARNING:"):
                    avisos.append(linha)
            processo.wait()
        finally:
            self.processo_ytdlp = None
        erro = None if processo.returncode == 0 and caminho else ("\n".join(erros) or "O download falhou sem mensagem de erro")
        return caminho, erro, avisos

    @staticmethod
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
        self.processo_corte = processo
        try:
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
        finally:
            self.processo_corte = None
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
    if len(sys.argv) > 1 and sys.argv[1] == "--ytdlp":
        # Modo usado pelo .exe para baixar num processo separado (equivale a "python -m yt_dlp")
        import yt_dlp
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        yt_dlp.main(sys.argv[2:])
        sys.exit(0)

    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
