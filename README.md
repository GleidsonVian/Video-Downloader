# Video-Downloader

Programa com interface gráfica para baixar vídeos do YouTube (até 1080p) e gerar cortes com nome a partir do vídeo baixado, prontos para enviar no WhatsApp.

## Funcionalidades

- Download em até 1080p, preferindo H.264 (abre em qualquer player e no celular)
- **Player para marcar cortes**: assista em 1x a 4x, clique em *Marcar início* e *Fechar corte* e o corte entra na lista (requer o [VLC](https://www.videolan.org/) de 64 bits)
- **Música de fundo**: baixe só o áudio (MP3, ~5 MB) e use como fundo dos cortes, misturada à voz ou no lugar do áudio original
- Vários cortes de uma vez, cada um com início, fim e nome próprios
- Corte exato no segundo pedido, com barra de progresso
- Opção **Caber no WhatsApp**: comprime cortes longos para ficarem abaixo de 180 MB
- Opção **Equilibrar volume do áudio**: aumenta falas baixas sem estourar o som alto
- Organização automática: `Vídeos/` para os downloads e `Cortes/<nome do vídeo>/` para os cortes
- Aviso quando os cookies do YouTube vencem

## Requisitos

- [Python 3.10+](https://www.python.org/downloads/) (com tkinter, que já vem no instalador do Windows)
- [FFmpeg](https://ffmpeg.org/) no PATH
- [Node.js](https://nodejs.org/) — o YouTube exige um runtime JavaScript para liberar os vídeos

No Windows, FFmpeg e Node.js podem ser instalados com:

```bash
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS
winget install --id VideoLAN.VLC -e --architecture x64
```

## Instalação

```bash
git clone https://github.com/GleidsonVian/Video-Downloader.git
cd Video-Downloader
python -m pip install -r requirements.txt
```

## Executável (.exe)

Para usar sem abrir terminal ou VS Code, dê dois cliques em **`build.bat`**. Ele atualiza o yt-dlp e gera o `Downloader Pro.exe` nesta pasta (leva uns 3 minutos).

- O `.exe` precisa ficar **nesta pasta**: é ao lado dele que ficam `Vídeos/`, `Cortes/` e o arquivo de cookies
- FFmpeg e Node.js continuam sendo necessários (veja Requisitos)
- O yt-dlp vai **dentro** do `.exe`. Quando o YouTube mudar algo e os downloads pararem de funcionar, rode o `build.bat` de novo para gerar um `.exe` atualizado

## Cookies do YouTube

Sem login, o YouTube costuma bloquear downloads com o erro *"Sign in to confirm you're not a bot"*. Para resolver:

1. Instale a extensão **Get cookies.txt LOCALLY** ([Chrome Web Store](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)) e permita o uso dela na janela anônima
2. Abra uma janela anônima, faça login no YouTube e acesse `youtube.com/robots.txt`
3. Clique na extensão → **Export**
4. Feche a janela anônima
5. Coloque o arquivo exportado (terminado em `cookies.txt`) na pasta do programa

> ⚠️ O arquivo de cookies dá acesso à sua conta do Google. Não compartilhe. Ele já está no `.gitignore` para não ir para o GitHub.

Se o Firefox estiver instalado e logado no YouTube, o programa usa os cookies dele automaticamente, sem precisar do arquivo.

## Uso

```bash
python main.py
```

**Janela principal** (baixar):
1. Cole o link e clique em **BAIXAR VÍDEO** (vai para `Vídeos/`) ou **♪ SÓ ÁUDIO (MP3)** (vai para `Músicas/`)
2. Clique em **✂ EDITAR VÍDEO** para abrir o editor. Ele usa o último vídeo baixado, e nada abre sozinho

**Editor** (cortes e música):
1. Preencha início e fim (minutos:segundos, ex: `15:05`) e o nome de cada corte, ou use **▶ ASSISTIR E MARCAR CORTES** para marcar assistindo (velocidade de 1x a 4x)
2. Use **+ Adicionar corte** (ou Enter no campo do nome) para mais cortes
3. Em **Áudio do corte**, escolha: *Original*, *Música de fundo (mistura)* (a música baixinha sob a voz, com volume e ponto de início ajustáveis) ou *Trocar pela música*. Música mais curta que o corte se repete
4. Clique em **GERAR CORTES**: eles vão para `Cortes/<nome do vídeo>/`

Também é possível editar qualquer vídeo que já esteja no PC com **Escolher vídeo do PC...** dentro do editor.

## Estrutura do código

```
main.py                    ponto de entrada (e o modo --ytdlp usado pelo .exe)
downloader_pro/
  config.py                pastas e constantes
  tempos.py                conversão de tempos (31:31 ↔ segundos)
  arquivos.py              nomes de arquivo, limpeza de temporários, abrir pasta
  cookies.py               cookies do YouTube
  ytdlp.py                 download de vídeo e MP3, tradução dos erros
  cortes.py                ffmpeg: corte, mistura de áudio, placa de vídeo
  player.py                player VLC para marcar cortes
  lista_cortes.py          tabela de cortes (início / fim / nome)
  painel_audio.py          escolha da música de fundo
  editor.py                janela do editor
  interface.py             janela principal (download)
  sistema.py               utilitários de janela e processos
```

## Problemas comuns

| Erro | Solução |
|---|---|
| `Sign in to confirm you're not a bot` | Exporte os cookies de novo (veja acima) |
| `No video formats found` / `page needs to be reloaded` | `python -m pip install -U "yt-dlp[default]"` |
| `This live event has ended` | A live acabou de terminar e o YouTube ainda está processando; tente mais tarde |
