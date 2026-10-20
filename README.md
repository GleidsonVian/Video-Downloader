# Video-Downloader

Programa com interface gráfica para baixar vídeos do YouTube (até 1080p) e gerar cortes com nome a partir do vídeo baixado, prontos para enviar no WhatsApp.

## Funcionalidades

- Download em até 1080p, preferindo H.264 (abre em qualquer player e no celular)
- **Player para marcar cortes**: assista em 1x a 4x, clique em *Marcar início* e *Fechar corte* e o corte entra na lista (requer o [VLC](https://www.videolan.org/) de 64 bits)
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

1. Cole o link e clique em **BAIXAR VÍDEO**
2. Em **Gerar cortes**, preencha início e fim (minutos:segundos, ex: `15:05`) e o nome de cada corte
3. Use **+ Adicionar corte** (ou Enter no campo do nome) para mais cortes
4. Clique em **GERAR CORTES**

Também é possível cortar qualquer vídeo que já esteja no PC com **Escolher outro vídeo do PC...**

## Problemas comuns

| Erro | Solução |
|---|---|
| `Sign in to confirm you're not a bot` | Exporte os cookies de novo (veja acima) |
| `No video formats found` / `page needs to be reloaded` | `python -m pip install -U "yt-dlp[default]"` |
| `This live event has ended` | A live acabou de terminar e o YouTube ainda está processando; tente mais tarde |
