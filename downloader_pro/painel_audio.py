"""Painel "Áudio do corte": áudio original, música de fundo (mistura) ou só a música."""
import os
import tkinter as tk
from tkinter import filedialog, ttk

from .arquivos import listar_musicas
from .config import EXT_AUDIO, PASTA_MUSICAS, PASTA_SCRIPT
from .tempos import para_segundos


class PainelAudio(tk.LabelFrame):
    def __init__(self, pai):
        super().__init__(pai, text=" Áudio do corte ", font=("Arial", 8, "bold"))
        self.musicas = {}  # nome mostrado -> caminho do arquivo

        linha_modo = tk.Frame(self)
        linha_modo.pack(fill=tk.X, padx=6, pady=(2, 0))
        self.modo = tk.StringVar(value="original")
        for valor, texto in (("original", "Original"), ("mistura", "Música de fundo (mistura)"),
                             ("musica", "Trocar pela música")):
            tk.Radiobutton(linha_modo, text=texto, value=valor, variable=self.modo,
                           command=self.atualizar_opcoes).pack(side=tk.LEFT, padx=4)

        self.linha_musica = tk.Frame(self)
        self.linha_musica.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.musica = tk.StringVar()
        self.combo = ttk.Combobox(self.linha_musica, textvariable=self.musica, state="readonly", width=34)
        self.combo.pack(side=tk.LEFT)
        tk.Button(self.linha_musica, text="...", width=3, command=self.escolher).pack(side=tk.LEFT, padx=(2, 8))
        tk.Label(self.linha_musica, text="Começar em:").pack(side=tk.LEFT)
        self.inicio = tk.Entry(self.linha_musica, width=6, justify="center")
        self.inicio.insert(0, "00:00")
        self.inicio.pack(side=tk.LEFT, padx=(2, 8))
        tk.Label(self.linha_musica, text="Volume:").pack(side=tk.LEFT)
        self.volume = tk.Scale(self.linha_musica, from_=5, to=100, orient="horizontal", length=90, showvalue=True)
        self.volume.set(30)
        self.volume.pack(side=tk.LEFT)

        self.atualizar_musicas()
        self.atualizar_opcoes()

    def atualizar_musicas(self, selecionar=None):
        """Lê a pasta Músicas/ e preenche a lista; 'selecionar' escolhe uma música (ex: a que acabou de baixar)"""
        if selecionar and os.path.dirname(os.path.abspath(selecionar)) != PASTA_MUSICAS:
            self.musicas[os.path.basename(selecionar)] = selecionar  # música de outra pasta
        self.musicas.update(listar_musicas())
        self.musicas = {n: c for n, c in self.musicas.items() if os.path.exists(c)}
        self.combo.config(values=list(self.musicas))
        if selecionar:
            self.musica.set(os.path.basename(selecionar))
        elif self.musica.get() not in self.musicas:
            self.musica.set(next(iter(self.musicas), ""))

    def escolher(self):
        caminho = filedialog.askopenfilename(
            title="Escolha a música", initialdir=PASTA_MUSICAS if os.path.isdir(PASTA_MUSICAS) else PASTA_SCRIPT,
            filetypes=[("Áudio", " ".join("*" + e for e in EXT_AUDIO)), ("Todos os arquivos", "*.*")])
        if caminho:
            self.atualizar_musicas(selecionar=os.path.normpath(caminho))

    def atualizar_opcoes(self):
        """Libera as opções da música só quando o modo precisa dela; o volume só vale na mistura"""
        ativo = self.modo.get() != "original"
        for filho in self.linha_musica.winfo_children():
            filho.config(state="normal" if ativo else "disabled")
        self.combo.config(state="readonly" if ativo else "disabled")
        if self.modo.get() == "musica":
            self.volume.config(state="disabled")

    def opcoes(self):
        """Opções para gerar_corte(): dict com modo_audio (e a música, se for usada).

        Levanta ValueError com a mensagem a mostrar ao usuário, se algo estiver faltando.
        """
        opcoes = {"modo_audio": self.modo.get()}
        if opcoes["modo_audio"] == "original":
            return opcoes
        if not self.musica.get():
            raise ValueError("Escolha uma música em \"Áudio do corte\", "
                             "ou baixe uma com o botão ♪ SÓ ÁUDIO (MP3).")
        try:
            inicio = para_segundos(self.inicio.get() or "0")
        except ValueError:
            raise ValueError("\"Começar em\" da música deve ser minutos:segundos (ex: 00:45).") from None
        opcoes.update(musica=self.musicas[self.musica.get()], volume_musica=self.volume.get(), inicio_musica=inicio)
        return opcoes
