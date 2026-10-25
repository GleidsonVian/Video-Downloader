"""Visual do programa (CustomTkinter): cores, fontes e componentes usados em todas as janelas."""
import customtkinter as ctk

from .config import ICONE

# Paleta escura
FUNDO = "#12141a"
CARTAO = "#1c1f27"
BORDA = "#2b303b"
CAMPO = "#14161c"
TEXTO = "#e9ebf1"
SUAVE = "#8e96aa"
AMARELO = "#f5a524"
VERDE_TEXTO = "#4cc38a"
VERMELHO_TEXTO = "#ff6b6b"

# (cor normal, cor com o mouse em cima)
VERMELHO = ("#e5484d", "#c93c41")
ROXO = ("#8e4ec6", "#7a3fb0")
AZUL = ("#3e63dd", "#3453c0")
VERDE = ("#30a46c", "#278a59")
CINZA = ("#2f3441", "#3d4352")


def iniciar():
    """Liga o tema escuro; chamar antes de criar a primeira janela"""
    ctk.set_appearance_mode("dark")


def fonte(tamanho=13, negrito=False):
    return ctk.CTkFont(family="Segoe UI", size=tamanho, weight="bold" if negrito else "normal")


def botao(pai, texto, cor=AZUL, comando=None, altura=40, **extra):
    return ctk.CTkButton(pai, text=texto, command=comando, fg_color=cor[0], hover_color=cor[1], height=altura,
                         corner_radius=10, font=fonte(13, True), text_color=TEXTO, **extra)


def botao_pequeno(pai, texto, comando=None, largura=30, cor_texto=TEXTO, **extra):
    """Botão discreto (sem fundo) para ações pequenas, como ▲ ▼ ✕"""
    return ctk.CTkButton(pai, text=texto, command=comando, width=largura, height=28, corner_radius=8,
                         fg_color="transparent", hover_color=CINZA[1], text_color=cor_texto, font=fonte(13, True),
                         **extra)


def cartao(pai, titulo=None):
    """Quadro arredondado que agrupa uma parte da tela, com título opcional"""
    quadro = ctk.CTkFrame(pai, fg_color=CARTAO, corner_radius=14, border_width=1, border_color=BORDA)
    if titulo:
        ctk.CTkLabel(quadro, text=titulo.upper(), font=fonte(11, True), text_color=SUAVE).pack(
            anchor="w", padx=16, pady=(12, 0))
    return quadro


def rotulo(pai, texto="", tamanho=13, negrito=False, suave=False, **extra):
    return ctk.CTkLabel(pai, text=texto, font=fonte(tamanho, negrito), text_color=SUAVE if suave else TEXTO, **extra)


def campo(pai, **extra):
    extra.setdefault("height", 34)
    return ctk.CTkEntry(pai, fg_color=CAMPO, border_color=BORDA, corner_radius=8, text_color=TEXTO,
                        font=fonte(13), **extra)


def chave(pai, texto, variavel, comando=None):
    """Interruptor liga/desliga"""
    return ctk.CTkSwitch(pai, text=texto, variable=variavel, command=comando, font=fonte(12),
                         progress_color=AZUL[0], text_color=TEXTO)


def menu(pai, valores, variavel=None, comando=None, largura=200):
    return ctk.CTkOptionMenu(pai, values=valores, variable=variavel, command=comando, width=largura, height=34,
                             corner_radius=8, fg_color=CAMPO, button_color=CINZA[0], button_hover_color=CINZA[1],
                             dropdown_fg_color=CARTAO, text_color=TEXTO, font=fonte(12))


def barra_progresso(pai, cor=AZUL):
    barra = ctk.CTkProgressBar(pai, height=10, corner_radius=5, fg_color=CAMPO, progress_color=cor[0])
    barra.set(0)
    return barra


def aplicar_icone(janela):
    """O CustomTkinter coloca o ícone padrão dele logo depois de abrir a janela; troca pelo nosso em seguida"""
    def trocar():
        try:
            janela.iconbitmap(ICONE)
        except Exception:
            pass
    janela.after(250, trocar)


def trazer_para_frente(janela):
    janela.deiconify()
    janela.lift()
    janela.after(100, janela.focus_force)
