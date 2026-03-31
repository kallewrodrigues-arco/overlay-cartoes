# 🗂️ Overlay de Cartões Resposta

Ferramenta para automatizar a sobreposição de redações reais nos cartões resposta, substituindo o conteúdo de resposta enquanto preserva o cabeçalho original.

---

## 📋 O que esta ferramenta faz

1. Lê o PDF com os cartões resposta
2. Recorta as imagens das respostas (opcional)
3. Sobrepõe cada resposta na área de resposta de cada cartão
4. Exporta os cartões finais como PNG, prontos para envio

---

## 💻 Requisitos

- Computador com **macOS**
- Conexão com a internet (apenas na primeira vez, para instalar)

---

## 🚀 Instalação (apenas na primeira vez)

### 1. Abra o Terminal

Pressione `Cmd + Espaço`, digite **Terminal** e pressione Enter.

### 2. Verifique se o Python está instalado

Cole o comando abaixo e pressione Enter:

```
python3 --version
```

- Se aparecer algo como `Python 3.11.x` → ✅ pode pular para o passo 3
- Se aparecer erro → acesse [python.org/downloads](https://www.python.org/downloads), baixe o instalador e siga as instruções. Depois volte aqui.

### 3. Instale as dependências

Cole os dois comandos abaixo no Terminal, um de cada vez, pressionando Enter após cada um:

```
pip3 install pymupdf
```

```
pip3 install pillow
```

Vai aparecer bastante texto rolando na tela — isso é normal. Aguarde até o cursor piscar novamente.

### 4. Verifique se a instalação deu certo

```
python3 -c "import fitz; import PIL; print('✅ Tudo instalado!')"
```

Se aparecer `✅ Tudo instalado!` está tudo pronto.

> ⚠️ Esses passos só precisam ser feitos uma vez. Na próxima vez, pode ir direto para o uso.

---

## 📁 Estrutura de pastas

Faça o unzip do pacote (no desktop é mais fácil de achar), a estrutura deve ficar assim:

```
overlay_cartoes/
├── cartao_overlay.py         → script principal
├── pre_crop_respostas.py      → script auxiliar de recorte
├── cartoes_resposta.pdf      → PDF baixado do sistema (você adiciona)
├── respostas/                 → imagens das respostas (você adiciona)
└── cartoes_finais/           → PNGs gerados (criado automaticamente)
```

---

## ▶️ Como usar

### Antes de começar

1. Coloque o PDF dos cartões resposta dentro da pasta `overlay_cartoes` com o nome `cartoes_resposta.pdf`
2. Coloque as imagens das redações (PNG ou JPG) dentro da pasta `redacoes`
3. Abra o Terminal e navegue até a pasta do projeto:

```
cd ~/Desktop/overlay_cartoes
```

> 💡 **Dica:** não sabe o caminho? Digite `cd ` (com espaço) no terminal. Depois, abra o Finder, navegue até a pasta `overlay_cartoes` e arraste ela para dentro da janela do Terminal. O caminho será preenchido automaticamente.

---

### Cenário 1 — Usar direto, sem recorte

Quando as imagens das redações já estão no formato ideal:

```
python3 cartao_overlay.py
```

Os cartões finais serão salvos na pasta `cartoes_finais`.

---

### Cenário 2 — Recortar as imagens antes

Quando as imagens têm texto de apoio no topo ou margem excessiva na base, use o script auxiliar antes.

**Só recortar o topo** (ex: remover 20% do topo):
```
python3 pre_crop_redacoes.py --topo 0.20
```

**Só recortar a base** (ex: remover 10% da base):
```
python3 pre_crop_redacoes.py --base 0.10
```

**Recortar topo e base ao mesmo tempo:**
```
python3 pre_crop_redacoes.py --topo 0.20 --base 0.10
```

As imagens recortadas serão salvas na pasta `redacoes_crop`. Depois, rode o script principal normalmente:

```
python3 cartao_overlay.py
```

---

### Cenário 3 — Recortar e gerar os cartões em um único comando

```
python3 pre_crop_redacoes.py --topo 0.20 --base 0.10 --overlay
```

O `--overlay` no final faz o script de recorte chamar o script principal automaticamente, sem precisar rodar dois comandos separados.

---

## ⚙️ Ajustes finos

Às vezes a sobreposição pode não ficar alinhada perfeitamente na primeira tentativa. Neste caso, abra o arquivo `cartao_overlay.py` em um editor de texto e ajuste os valores da seção `CONFIGURAÇÃO`:

```python
AREA_RESPOSTA = {
    "top_pct": 0.30,  # onde o cabeçalho termina (ajuste este valor)
}
```

- Se a redação cobrir parte do cabeçalho → **aumente** o valor (ex: `0.35`)
- Se ficar uma faixa em branco entre o cabeçalho e a redação → **diminua** o valor (ex: `0.25`)

---

## ❓ Dúvidas frequentes

**O Terminal mostrou um erro em vermelho. O que faço?**
Copie o texto do erro e mande para quem te passou esta ferramenta.

**A pasta `cartoes_finais` está vazia após rodar.**
Verifique se o PDF está na pasta com o nome exato `cartoes_resposta.pdf` e se há imagens dentro da pasta `redacoes`.

**Posso rodar a ferramenta mais de uma vez?**
Sim. A cada execução, os arquivos anteriores na pasta `cartoes_finais` são substituídos pelos novos.

**Precisa de internet para usar?**
Não, apenas na primeira vez para instalar as dependências.
