"""
app.py
------
Aplicação web para sobreposição de respostas em cartões resposta.
Desenvolvida com Streamlit.

Dependências:
    pip install streamlit pymupdf pillow
"""

import io
import zipfile

import streamlit as st
from PIL import Image, ImageDraw
import fitz  # PyMuPDF


# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

AREA_RESPOSTA_PADRAO = {
    "left_pct":   0.03,
    "top_pct":    0.30,
    "right_pct":  0.97,
    "bottom_pct": 0.97,
}

DPI = 200

# ─────────────────────────────────────────────


def pdf_para_imagens(pdf_bytes: bytes, dpi: int) -> list[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    imagens = []
    for pagina in doc:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = pagina.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        imagens.append(img)
    doc.close()
    return imagens


def aplicar_crop(img: Image.Image, cortar_topo: float, cortar_base: float) -> Image.Image:
    largura, altura = img.size
    y_inicio = int(altura * cortar_topo)
    y_fim    = int(altura * (1 - cortar_base))
    if y_inicio >= y_fim:
        return img
    return img.crop((0, y_inicio, largura, y_fim))


def sobrepor_resposta(cartao: Image.Image, resposta: Image.Image, area: dict) -> Image.Image:
    resultado = cartao.copy()
    largura, altura = cartao.size

    x0 = int(largura * area["left_pct"])
    y0 = int(altura  * area["top_pct"])
    x1 = int(largura * area["right_pct"])
    y1 = int(altura  * area["bottom_pct"])
    area_w = x1 - x0
    area_h = y1 - y0

    ratio  = max(area_w / resposta.width, area_h / resposta.height)
    novo_w = int(resposta.width  * ratio)
    novo_h = int(resposta.height * ratio)
    resposta = resposta.resize((novo_w, novo_h), Image.LANCZOS)

    crop_x = (novo_w - area_w) // 2
    crop_y = (novo_h - area_h) // 2
    resposta = resposta.crop((crop_x, crop_y, crop_x + area_w, crop_y + area_h))

    resultado.paste(resposta, (x0, y0))
    return resultado


def imagem_para_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def primeira_imagem(arquivos) -> Image.Image | None:
    """Extrai a primeira imagem ou primeira página do primeiro arquivo enviado."""
    if not arquivos:
        return None
    arq = sorted(arquivos, key=lambda f: f.name)[0]
    arq.seek(0)
    if arq.type == "application/pdf":
        paginas = pdf_para_imagens(arq.read(), DPI)
        return paginas[0] if paginas else None
    else:
        return Image.open(arq).convert("RGB")


def gerar_preview(img: Image.Image, cortar_topo: float, cortar_base: float) -> Image.Image:
    """Desenha linhas de corte vermelhas sobre o preview da imagem."""
    preview = img.copy()
    # Reduz para caber bem na tela
    max_h = 500
    if preview.height > max_h:
        ratio = max_h / preview.height
        preview = preview.resize(
            (int(preview.width * ratio), max_h), Image.LANCZOS
        )

    w, h = preview.size
    draw = ImageDraw.Draw(preview)
    espessura = 3

    if cortar_topo > 0:
        y_topo = int(h * cortar_topo)
        # Área descartada no topo — overlay semitransparente
        overlay = Image.new("RGBA", (w, y_topo), (255, 0, 0, 60))
        preview = preview.convert("RGBA")
        preview.paste(overlay, (0, 0), overlay)
        preview = preview.convert("RGB")
        draw = ImageDraw.Draw(preview)
        draw.line([(0, y_topo), (w, y_topo)], fill="red", width=espessura)
        draw.text((8, y_topo - 18), f"▲ cortar topo ({int(cortar_topo*100)}%)", fill="red")

    if cortar_base > 0:
        y_base = int(h * (1 - cortar_base))
        overlay = Image.new("RGBA", (w, h - y_base), (255, 0, 0, 60))
        preview = preview.convert("RGBA")
        preview.paste(overlay, (0, y_base), overlay)
        preview = preview.convert("RGB")
        draw = ImageDraw.Draw(preview)
        draw.line([(0, y_base), (w, y_base)], fill="red", width=espessura)
        draw.text((8, y_base + 6), f"▼ cortar base ({int(cortar_base*100)}%)", fill="red")

    return preview


# ─────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────

st.set_page_config(page_title="Overlay Cartões Resposta", page_icon="🗂️", layout="centered")

st.title("🗂️ Overlay de Cartões Resposta")
st.caption("Sobreponha respostas nos cartões preservando o cabeçalho.")

st.divider()

# --- Upload ---
st.subheader("1. Arquivos")

col1, col2 = st.columns(2)

with col1:
    pdf_cartoes = st.file_uploader(
        "PDF dos cartões resposta",
        type=["pdf"],
        help="O PDF baixado do sistema com os cartões."
    )

with col2:
    arquivos_respostas = st.file_uploader(
        "Respostas (imagens ou PDF)",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
        help="Imagens avulsas (PNG/JPG) ou um PDF com todas as respostas."
    )

st.divider()

# --- Crop ---
st.subheader("2. Recorte das respostas (opcional)")
st.caption("Ative o recorte para remover texto de apoio no topo ou margens excessivas na base.")

aplicar_crop_flag = st.toggle("Ativar recorte", value=False)

cortar_topo = 0.0
cortar_base = 0.0

if aplicar_crop_flag:
    col_sliders, col_preview = st.columns([1, 1], gap="large")

    with col_sliders:
        st.markdown("**Ajuste os cortes**")
        cortar_topo = st.slider(
            "Remover do topo (%)",
            min_value=0, max_value=50, value=0, step=1,
            help="Percentual removido do topo de cada resposta."
        ) / 100
        cortar_base = st.slider(
            "Remover da base (%)",
            min_value=0, max_value=50, value=0, step=1,
            help="Percentual removido da base de cada resposta."
        ) / 100

        if cortar_topo == 0 and cortar_base == 0:
            st.info("Mova os sliders para visualizar o corte.")

    with col_preview:
        st.markdown("**Preview**")
        if arquivos_respostas:
            img_preview = primeira_imagem(arquivos_respostas)
            if img_preview:
                preview = gerar_preview(img_preview, cortar_topo, cortar_base)
                st.image(preview, use_container_width=True)
        else:
            st.caption("⬆️ Faça o upload das respostas para ver o preview aqui.")

st.divider()

# --- Área de resposta ---
st.subheader("3. Área de resposta no cartão")
st.caption("Define onde a resposta será colada. Ajuste apenas se a sobreposição não ficar alinhada.")

top_pct = AREA_RESPOSTA_PADRAO["top_pct"]

with st.expander("⚙️ Ajustes avançados"):
    top_pct = st.slider(
        "Onde o cabeçalho termina (% do topo)",
        min_value=0, max_value=80, value=30, step=1,
        help="Aumente se a resposta cobrir o cabeçalho. Diminua se ficar uma faixa em branco."
    ) / 100

area = {**AREA_RESPOSTA_PADRAO, "top_pct": top_pct}

st.divider()

# --- Processamento ---
st.subheader("4. Gerar cartões")

if st.button("🚀 Gerar cartões", use_container_width=True, type="primary"):

    if not pdf_cartoes:
        st.error("⚠️ Faça o upload do PDF dos cartões resposta.")
        st.stop()

    if not arquivos_respostas:
        st.error("⚠️ Faça o upload de pelo menos uma resposta.")
        st.stop()

    with st.spinner("Processando..."):

        cartoes = pdf_para_imagens(pdf_cartoes.read(), DPI)

        respostas = []
        for arq in sorted(arquivos_respostas, key=lambda f: f.name):
            arq.seek(0)
            if arq.type == "application/pdf":
                paginas = pdf_para_imagens(arq.read(), DPI)
                respostas.extend(paginas)
            else:
                img = Image.open(arq).convert("RGB")
                respostas.append(img)

        if aplicar_crop_flag:
            respostas = [aplicar_crop(r, cortar_topo, cortar_base) for r in respostas]

        if len(respostas) < len(cartoes):
            st.warning(
                f"⚠️ Há menos respostas ({len(respostas)}) do que cartões ({len(cartoes)}). "
                "Os cartões sem par serão exportados sem sobreposição."
            )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, cartao in enumerate(cartoes):
                if i < len(respostas):
                    cartao_final = sobrepor_resposta(cartao, respostas[i], area)
                else:
                    cartao_final = cartao
                zf.writestr(f"cartao_{i+1:03d}.png", imagem_para_bytes(cartao_final))

        zip_buffer.seek(0)

    st.success(f"✅ {len(cartoes)} cartão(ões) gerado(s) com sucesso!")

    st.download_button(
        label="📥 Baixar cartões (ZIP)",
        data=zip_buffer,
        file_name="cartoes_finais.zip",
        mime="application/zip",
        use_container_width=True
    )
