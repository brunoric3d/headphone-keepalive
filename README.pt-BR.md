<p align="center">
  <img src="assets/keepalive_logo.png" width="140" alt="Headphone Keep Alive">
</p>

<h1 align="center">Headphone Keep Alive</h1>

<p align="center">
  Um app pequeno de bandeja que toca um som quase inaudível para que fones que desligam sozinhos continuem ligados.<br>
  Windows, macOS e Linux, com o mesmo código.
</p>

<p align="center">
  <a href="https://github.com/brunoric3d/headphone-keepalive/releases/latest">Baixar</a> ·
  <a href="README.md">English</a>
</p>

---

Muito fone bluetooth desliga depois de alguns minutos sem áudio. Se você trabalha em silêncio e só ouve alguma coisa de vez em quando, ele fica morrendo na sua mão. Este app mantém um sinal contínuo e inaudível na saída, então o fone sempre acha que tem algo tocando.

## Instalar

Pegue o arquivo do seu sistema no [release mais recente](https://github.com/brunoric3d/headphone-keepalive/releases/latest).

| Sistema | Arquivo | Observação |
| --- | --- | --- |
| Windows | `HeadphoneKeepAlive-windows-x64.exe` | É só rodar. O SmartScreen pode avisar sobre editor desconhecido: clique em "Mais informações" e depois em "Executar assim mesmo". |
| macOS Apple Silicon | `HeadphoneKeepAlive-macos-arm64.zip` | Descompacte em Aplicativos. Na primeira vez: `xattr -dr com.apple.quarantine HeadphoneKeepAlive.app` |
| macOS Intel | `HeadphoneKeepAlive-macos-x64.zip` | Igual ao de cima. |
| Linux | `HeadphoneKeepAlive-linux-x64` | Dê `chmod +x` e rode. Precisa de um host de bandeja. Veja as notas de Linux abaixo. |

Cada download é um arquivo só. O macOS é a exceção: um `.app` é uma pasta, então
ele precisa viajar dentro de um zip.

Os arquivos não têm assinatura digital, então Windows e macOS vão perguntar antes de rodar. Isso é normal em projeto aberto sem certificado pago.

## Rodar pelo código

Python 3.10 ou mais novo. As versões das dependências estão travadas no `requirements.txt`.

```bash
pip install -r requirements.txt
python run.py
```

No Linux ainda pode faltar o PortAudio e o suporte de bandeja:

```bash
# Debian, Ubuntu, Mint
sudo apt install libportaudio2 gir1.2-ayatanaappindicator3-0.1 python3-gi

# Fedora
sudo dnf install portaudio libayatana-appindicator-gtk3 python3-gobject
```

No GNOME talvez seja preciso a extensão AppIndicator Support para o ícone aparecer.

## Usando

O ícone fica violeta enquanto o som está tocando, cinza quando está parado e vermelho quando não achou saída de áudio.

**Som**

| Opção | Quando usar |
| --- | --- |
| Ruído rosa | O padrão. Tem energia espalhada por todo o espectro, então passa por qualquer codec bluetooth |
| Ruído marrom | Mais grave e mais abafado. Bom se o ruído rosa incomodar em ambiente muito silencioso |
| Tom grave 20 Hz | Inaudível para quase todo mundo, mas vários fones cortam essa faixa e dormem mesmo assim |
| Tom agudo 19 kHz | Inaudível para a maioria dos adultos, mas alguns codecs bluetooth cortam acima de 16 kHz |
| Pulso curto | Um estalo baixíssimo a cada X segundos. Gasta menos bateria, mas só funciona se o fone esperar mais que o intervalo |

Comece no ruído rosa. Os tons puros só valem a pena se você quiser silêncio absoluto e o seu fone aceitar.

**Volume** vai de -66 dBFS até -30 dBFS. O padrão é -54 dBFS, que é inaudível em uso normal e ainda bem acima do silêncio digital. Se o fone continuar desligando, suba um passo por vez.

**Saída de áudio** deixa você seguir o padrão do sistema ou fixar um dispositivo. O Windows expõe o mesmo fone uma vez para cada API de áudio (MME, DirectSound, WASAPI e WDM-KS), então a lista crua vem cheia de repetição, e no MME os nomes ainda chegam cortados em 31 caracteres. O app mostra só a API preferida de cada sistema, WASAPI no Windows, Core Audio no macOS, PulseAudio ou PipeWire no Linux, e tira nomes repetidos dentro da mesma API. Ligue "Mostrar todas as APIs de áudio" se quiser forçar um caminho específico.

**Seguir a saída padrão do sistema** leva o som para a saída que o sistema estiver usando. No Windows o app pergunta ao sistema quantas saídas existem, o que não custa nada e não encosta no áudio, e só reconecta quando um dispositivo realmente entra ou sai. No macOS e no Linux não existe um sinal igualmente barato, então ele cai para uma checagem a cada 60 segundos. Nos dois casos o stream só é reaberto quando algo mudou de verdade. Desligue se você fixou um dispositivo.

**Iniciar com o sistema** cria a entrada de inicialização no lugar certo de cada sistema.

- Windows: chave `Run` em `HKEY_CURRENT_USER`
- macOS: um LaunchAgent em `~/Library/LaunchAgents`
- Linux: um `.desktop` em `~/.config/autostart`

**Idioma** segue o sistema operacional e cai no inglês quando não conhece. Dá para trocar na mão pelo menu. Disponíveis: English, Português, Español, Deutsch, Français, Italiano, 中文, 日本語, Русский.

## Linha de comando

```bash
python run.py --list-devices     # saídas de áudio, sem repetição
python run.py --list-devices --all-apis
python run.py --list-languages
python run.py --licenses         # grava em disco os textos de licença de terceiros
python run.py --headless         # sem ícone, útil para testar
python run.py --version
```

## Onde ficam as configurações

- Windows: `%APPDATA%\headphone-keepalive\config.json`
- macOS: `~/Library/Application Support/headphone-keepalive/config.json`
- Linux: `~/.config/headphone-keepalive/config.json`

## Como funciona

O ruído é renderizado na hora do build pelo `tools/make_audio.py`, que usa NumPy para moldar o espectro numa FFT, corta tudo abaixo de 30 Hz e mistura 50 ms do fim sobre o começo, para o loop fechar sem clique. O resultado vai para `assets/` como PCM cru de 16 bits. O NumPy é dependência só de build, e é isso que mantém o executável em torno de 12 MB em vez de 36 MB. Os tons são baratos o bastante para nascer na inicialização, na taxa real do dispositivo, com buffer de exatamente um segundo e frequência inteira, então o loop fecha na fase certa.

Em execução o app monta um único buffer com o volume aplicado e os canais montados, e o callback de áudio não faz nada além de copiar bytes dele. Nada é calculado nem alocado no caminho de tempo real. Trocar o som, o volume ou o intervalo do pulso substitui esse buffer no lugar, então essas mudanças valem na hora, sem encostar no stream e sem nenhum corte no áudio.

Um watchdog checa o stream a cada 5 segundos e reabre se ele morreu, porque o fone caiu ou o driver derrubou. Reabrir não reconstrói mais o buffer, então o silêncio que isso custava caiu de uns 400 ms para menos de 10 ms. A taxa de amostragem e o número de canais são negociados com o driver, com queda para 44100, 32000 e 22050 se a placa recusar. Os arquivos de ruído são de 48 kHz; tocá-los em outra taxa desloca o espectro um pouco, o que para ruído não muda nada que dê para ouvir.

## Gerar os executáveis

Os scripts instalam sozinhos o que precisam, incluindo o PyInstaller, a partir
do `requirements-build.txt`. Rode a partir da pasta do projeto.

```bash
# Windows
build_windows.bat

# macOS
bash build_macos.sh

# Linux
bash build_linux.sh
```

Para instalar as ferramentas de build na mão:

```bash
pip install -r requirements-build.txt
```

O PyInstaller fica de propósito fora do `requirements.txt`, para quem só quer
rodar o app não precisar baixar uma cadeia de build inteira.

O resultado sai na pasta `dist`. Os releases são montados pelo GitHub Actions a cada tag `v*`, em quatro máquinas diferentes, e anexados a um release em rascunho.

## Problemas comuns

**O fone continua desligando.** Suba o volume um passo e volte para ruído rosa se estiver em um tom puro. Alguns fones checam a energia numa faixa específica.

**Escuto um chiado leve.** Desça o volume um passo, ou troque para ruído marrom, que é menos perceptível.

**O ícone fica vermelho.** Não há saída de áudio disponível. Abra "Saída de áudio" e clique em "Atualizar lista".

**O som não vai para o fone que acabei de conectar.** Confirme que "Seguir a saída padrão do sistema" está marcado, ou escolha o fone direto na lista.

## Traduções

O app vem com nove idiomas, em `keepalive/i18n.py`. Adicionar um novo é só criar um dicionário com as mesmas 31 chaves. Correções nos que já existem são bem-vindas, principalmente nos idiomas que o autor não fala.

## Licença

CC0 1.0 Universal. O autor abre mão dos direitos autorais e conexos sobre este
trabalho no mundo todo, até onde a lei permite. Faça o que quiser com ele, sem
precisar dar crédito. Veja o [LICENSE](LICENSE).

Essa renúncia vale só para o código deste projeto. As bibliotecas que ele usa
mantêm as licenças delas, e a pystray em especial é LGPL-3.0, o que impõe
condições sobre os executáveis prontos. Veja o
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

O aviso e os textos completos da LGPL e da GPL viajam dentro do executável,
então chegam a quem baixa. Rode com `--licenses` e ele grava tudo numa pasta ao
lado dele.
