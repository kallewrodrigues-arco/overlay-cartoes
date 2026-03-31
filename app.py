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


def aplicar_crop(img: Image.Image, cortar_topo: float, cortar_base: float, cortar_esq: float, cortar_dir: float) -> Image.Image:
    largura, altura = img.size
    x0 = int(largura * cortar_esq)
    x1 = int(largura * (1 - cortar_dir))
    y0 = int(altura  * cortar_topo)
    y1 = int(altura  * (1 - cortar_base))
    if x0 >= x1 or y0 >= y1:
        return img
    return img.crop((x0, y0, x1, y1))


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
    if not arquivos:
        return None
    arq = sorted(arquivos, key=lambda f: f.name)[0]
    arq.seek(0)
    if arq.type == "application/pdf":
        paginas = pdf_para_imagens(arq.read(), DPI)
        return paginas[0] if paginas else None
    else:
        return Image.open(arq).convert("RGB")


def redimensionar_preview(img: Image.Image, max_h: int = 500) -> Image.Image:
    if img.height > max_h:
        ratio = max_h / img.height
        return img.resize((int(img.width * ratio), max_h), Image.LANCZOS)
    return img.copy()


def gerar_preview_crop(img: Image.Image, cortar_topo: float, cortar_base: float, cortar_esq: float, cortar_dir: float) -> Image.Image:
    preview = redimensionar_preview(img)
    w, h = preview.size
    espessura = 3

    x0 = int(w * cortar_esq)
    x1 = int(w * (1 - cortar_dir))
    y0 = int(h * cortar_topo)
    y1 = int(h * (1 - cortar_base))

    # Áreas descartadas — overlay vermelho
    regioes = []
    if cortar_topo > 0:  regioes.append((0, 0, w, y0))
    if cortar_base > 0:  regioes.append((0, y1, w, h))
    if cortar_esq  > 0:  regioes.append((0, y0, x0, y1))
    if cortar_dir  > 0:  regioes.append((x1, y0, w, y1))

    if regioes:
        preview = preview.convert("RGBA")
        for rx0, ry0, rx1, ry1 in regioes:
            rw, rh = rx1 - rx0, ry1 - ry0
            if rw > 0 and rh > 0:
                ov = Image.new("RGBA", (rw, rh), (255, 0, 0, 60))
                preview.paste(ov, (rx0, ry0), ov)
        preview = preview.convert("RGB")

    draw = ImageDraw.Draw(preview)

    # Retângulo da área mantida
    draw.rectangle([(x0, y0), (x1, y1)], outline="green", width=espessura)

    # Labels
    if cortar_topo > 0: draw.text((x0 + 4, y0 - 18), f"▲ topo ({int(cortar_topo*100)}%)", fill="red")
    if cortar_base > 0: draw.text((x0 + 4, y1 + 4),  f"▼ base ({int(cortar_base*100)}%)", fill="red")
    if cortar_esq  > 0: draw.text((4, y0 + 4),        f"esq\n({int(cortar_esq*100)}%)",    fill="red")
    if cortar_dir  > 0: draw.text((x1 + 4, y0 + 4),   f"dir\n({int(cortar_dir*100)}%)",    fill="red")

    return preview


def gerar_preview_cartao(img: Image.Image, top_pct: float, bottom_pct: float, left_pct: float, right_pct: float) -> Image.Image:
    preview = redimensionar_preview(img)
    w, h = preview.size

    x0 = int(w * left_pct)
    y0 = int(h * top_pct)
    x1 = int(w * (1 - right_pct))
    y1 = int(h * (1 - bottom_pct))

    preview = preview.convert("RGBA")
    cor_margem   = (0, 100, 255, 50)
    cor_resposta = (0, 200, 100, 30)

    overlay_resp = Image.new("RGBA", (x1 - x0, y1 - y0), cor_resposta)
    preview.paste(overlay_resp, (x0, y0), overlay_resp)

    for rect in [
        (0, 0, w, y0),
        (0, y1, w, h),
        (0, y0, x0, y1),
        (x1, y0, w, y1),
    ]:
        rx0, ry0, rx1, ry1 = rect
        rw, rh = rx1 - rx0, ry1 - ry0
        if rw > 0 and rh > 0:
            ov = Image.new("RGBA", (rw, rh), cor_margem)
            preview.paste(ov, (rx0, ry0), ov)

    preview = preview.convert("RGB")
    draw = ImageDraw.Draw(preview)
    draw.rectangle([(x0, y0), (x1, y1)], outline=(0, 150, 80), width=2)

    if y0 > 14:
        draw.text((x0 + 4, y0 - 16), f"topo ({int(top_pct*100)}%)", fill=(0, 100, 255))
    if y1 < h - 4:
        draw.text((x0 + 4, y1 + 4), f"base ({int(bottom_pct*100)}%)", fill=(0, 100, 255))
    if x0 > 4:
        draw.text((4, y0 + 4), f"esq\n({int(left_pct*100)}%)", fill=(0, 100, 255))
    if x1 < w - 4:
        draw.text((x1 + 4, y0 + 4), f"dir\n({int(right_pct*100)}%)", fill=(0, 100, 255))

    return preview


# ─────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────

st.set_page_config(page_title="Overlay Cartões Resposta", page_icon="🗂️", layout="centered")

st.title("🗂️ Overlay de Cartões Resposta")
st.caption("Sobreponha respostas nos cartões preservando o cabeçalho.")

st.divider()

# ── 1. Cartões em branco ─────────────────────
st.subheader("1. Cartões em branco")
st.caption("Envie o PDF dos cartões em branco que receberão as respostas.")

pdf_cartoes = st.file_uploader(
    "PDF dos cartões em branco",
    type=["pdf"],
    help="O PDF baixado do sistema com os cartões."
)

st.divider()

# ── 2. Área da resposta ──────────────────────
st.subheader("2. Área da resposta")
st.caption("Marque as margens que devem ser preservadas. A área verde é onde as respostas serão coladas.")

col_slider_cartao, col_preview_cartao = st.columns([1, 1], gap="large")

with col_slider_cartao:
    st.markdown("**Ajuste as margens**")
    top_pct = st.slider(
        "Topo — cabeçalho (%)",
        min_value=0, max_value=80, value=30, step=1,
        help="Percentual do topo preservado (cabeçalho)."
    ) / 100
    bottom_pct = st.slider(
        "Base (%)",
        min_value=0, max_value=50, value=3, step=1,
        help="Percentual da base preservado."
    ) / 100
    left_pct = st.slider(
        "Lateral esquerda (%)",
        min_value=0, max_value=30, value=3, step=1,
        help="Percentual da lateral esquerda preservado."
    ) / 100
    right_pct = st.slider(
        "Lateral direita (%)",
        min_value=0, max_value=30, value=3, step=1,
        help="Percentual da lateral direita preservado."
    ) / 100
    st.markdown("🔵 Azul = margens preservadas")
    st.markdown("🟢 Verde = área onde a resposta será colada")

with col_preview_cartao:
    st.markdown("**Preview**")
    if pdf_cartoes:
        pdf_cartoes.seek(0)
        paginas_cartao = pdf_para_imagens(pdf_cartoes.read(), DPI)
        if paginas_cartao:
            st.image(gerar_preview_cartao(paginas_cartao[0], top_pct, bottom_pct, left_pct, right_pct), use_container_width=True)
    else:
        st.caption("⬆️ Envie o PDF dos cartões na seção 1 para ver o preview aqui.")

area = {
    "left_pct":   left_pct,
    "top_pct":    top_pct,
    "right_pct":  1 - right_pct,
    "bottom_pct": 1 - bottom_pct,
}

st.divider()

# ── 3. Respostas ─────────────────────────────
st.subheader("3. Respostas")
st.caption("Envie aqui os arquivos com as respostas que serão coladas nos cartões em branco.")

arquivos_respostas = st.file_uploader(
    "Respostas (imagens ou PDF)",
    type=["png", "jpg", "jpeg", "pdf"],
    accept_multiple_files=True,
    help="Imagens avulsas (PNG/JPG) ou um PDF com todas as respostas."
)

st.divider()

# ── 4. Recorte das respostas ─────────────────
st.subheader("4. Recorte das respostas (opcional)")
st.caption("Ative o recorte para remover texto de apoio no topo ou margens excessivas na base.")

aplicar_crop_flag = st.toggle("Ativar recorte", value=False)

cortar_topo = 0.0
cortar_base = 0.0
cortar_esq  = 0.0
cortar_dir  = 0.0

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
        cortar_esq = st.slider(
            "Remover da lateral esquerda (%)",
            min_value=0, max_value=30, value=0, step=1,
            help="Percentual removido da lateral esquerda de cada resposta."
        ) / 100
        cortar_dir = st.slider(
            "Remover da lateral direita (%)",
            min_value=0, max_value=30, value=0, step=1,
            help="Percentual removido da lateral direita de cada resposta."
        ) / 100
        if cortar_topo == 0 and cortar_base == 0 and cortar_esq == 0 and cortar_dir == 0:
            st.info("Mova os sliders para visualizar o corte.")

    with col_preview:
        st.markdown("**Preview**")
        if arquivos_respostas:
            img_preview = primeira_imagem(arquivos_respostas)
            if img_preview:
                st.image(gerar_preview_crop(img_preview, cortar_topo, cortar_base, cortar_esq, cortar_dir), use_container_width=True)
        else:
            st.caption("⬆️ Envie as respostas na seção 3 para ver o preview aqui.")

st.divider()

# ── 5. Gerar cartões ─────────────────────────
st.subheader("5. Gerar cartões")

if st.button("🚀 Gerar cartões", use_container_width=True, type="primary"):

    if not pdf_cartoes:
        st.error("⚠️ Envie o PDF dos cartões em branco na seção 1.")
        st.stop()

    if not arquivos_respostas:
        st.error("⚠️ Envie as respostas na seção 3.")
        st.stop()

    with st.spinner("Processando..."):

        pdf_cartoes.seek(0)
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
            respostas = [aplicar_crop(r, cortar_topo, cortar_base, cortar_esq, cortar_dir) for r in respostas]

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
