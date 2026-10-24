"""Player (VLC) para assistir o vídeo e marcar o início/fim dos cortes."""
import os
import tkinter as tk
from tkinter import messagebox

from .tempos import tempo_curto


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
    """Janela para assistir o vídeo (com velocidade ajustável) e marcar início/fim dos cortes.

    Cada corte fechado é entregue à lista de cortes da janela principal (ListaCortes).
    """

    VELOCIDADES = (1, 1.5, 2, 3, 4)
    FUNDO = "#1e1e1e"

    def __init__(self, janela_pai, caminho, vlc, lista_cortes):
        self.lista = lista_cortes
        self.vlc = vlc
        self.inicio_marcado = None  # segundos do início do corte em andamento
        self.arrastando = None      # posição (s) enquanto o mouse arrasta a linha do tempo
        self.marcados = 0

        self.janela = tk.Toplevel(janela_pai)
        self.janela.title(f"Assistir e marcar — {os.path.basename(caminho)}")
        self.janela.geometry("1000x720")
        self.janela.minsize(640, 420)
        self.janela.configure(bg=self.FUNDO)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        self.criar_widgets()

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

    def criar_widgets(self):
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

        self.info_label = tk.Label(
            self.janela, bg=self.FUNDO, fg="#aaa", font=("Arial", 9),
            text="Espaço: pausar  •  ← →: 5s  •  ↑ ↓: velocidade  •  M: marcar  •  Esc: cancelar marcação")
        self.info_label.pack(pady=(0, 8))

        for tecla, acao in (("<space>", lambda e: self.play_pause()), ("<Left>", lambda e: self.pular(-5)),
                            ("<Right>", lambda e: self.pular(5)), ("<Up>", lambda e: self.passo_velocidade(1)),
                            ("<Down>", lambda e: self.passo_velocidade(-1)), ("<m>", lambda e: self.marcar()),
                            ("<M>", lambda e: self.marcar()), ("<Escape>", lambda e: self.cancelar_marcacao())):
            self.janela.bind(tecla, acao)

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
        for inicio, fim, _ in self.lista.ler_cortes()[0]:
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
            self.lista.adicionar_corte(int(inicio), int(fim) + (fim % 1 > 0))
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
