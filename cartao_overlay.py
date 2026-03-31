"""
overlay_cartoes.py
------------------
Extrai páginas de um PDF de cartões resposta, sobrepõe imagens de redações
na área de resposta (região fixa) e exporta cada cartão como PNG.

Dependências:
    pip install pymupdf pillow
"""

from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF


# ─────────────────────────────────────────────
# CONFIGURAÇÃO — ajuste conforme seu cartão
# ─────────────────────────────────────────────

PDF_CARTOES    = "cartoes_resposta.pdf"   # PDF baixado do client-face
PASTA_REDACOES = "respostas_crop/"             # Pasta com PNGs/JPEGs das redações
PASTA_SAIDA    = "cartoes_finais/"       # Onde os PNGs finais serão salvos

# Região de resposta em percentual da página (0.0 a 1.0)
# Ajuste olhando o cartão: top_pct = onde o cabeçalho termina
AREA_RESPOSTA = {
    "left_pct":   0.03,   # margem esquerda
    "top_pct":    0.38,   # ← PRINCIPAL: onde o cabeçalho termina
    "right_pct":  0.97,   # margem direita
    "bottom_pct": 0.95,   # margem inferior
}

DPI = 200  # Resolução da extração do PDF (150–300 é o ideal)

# ─────────────────────────────────────────────


def pdf_para_imagens(pdf_path: str, dpi: int) -> list[Image.Image]:
    """Extrai cada página do PDF como imagem PIL."""
    doc = fitz.open(pdf_path)
    imagens = []
    for pagina in doc:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = pagina.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        imagens.append(img)
    doc.close()
    return imagens


def listar_redacoes(pasta: str) -> list[Path]:
    """Lista arquivos de imagem na pasta, ordenados por nome."""
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted(
        p for p in Path(pasta).iterdir()
        if p.suffix.lower() in exts
    )


def calcular_area_px(largura: int, altura: int, area: dict) -> tuple[int, int, int, int]:
    """Converte percentuais para pixels."""
    x0 = int(largura * area["left_pct"])
    y0 = int(altura  * area["top_pct"])
    x1 = int(largura * area["right_pct"])
    y1 = int(altura  * area["bottom_pct"])
    return x0, y0, x1, y1


def sobrepor_redacao(cartao: Image.Image, redacao_path: Path, area: dict) -> Image.Image:
    """Cola a imagem da redação na área de resposta do cartão."""
    resultado = cartao.copy()
    largura, altura = cartao.size

    x0, y0, x1, y1 = calcular_area_px(largura, altura, area)
    area_largura = x1 - x0
    area_altura  = y1 - y0

    redacao = Image.open(redacao_path).convert("RGB")

    # Redimensiona a redação para preencher exatamente a área (sem distorção lateral,
    # mantendo proporção e cortando o excesso)
    ratio = max(area_largura / redacao.width, area_altura / redacao.height)
    novo_w = int(redacao.width  * ratio)
    novo_h = int(redacao.height * ratio)
    redacao = redacao.resize((novo_w, novo_h), Image.LANCZOS)

    # Centraliza e recorta para o tamanho exato da área
    crop_x = (novo_w - area_largura) // 2
    crop_y = (novo_h - area_altura)  // 2
    redacao = redacao.crop((crop_x, crop_y, crop_x + area_largura, crop_y + area_altura))

    resultado.paste(redacao, (x0, y0))
    return resultado


def main():
    saida = Path(PASTA_SAIDA)
    saida.mkdir(parents=True, exist_ok=True)

    print(f"📄 Extraindo páginas de '{PDF_CARTOES}'...")
    cartoes = pdf_para_imagens(PDF_CARTOES, DPI)
    print(f"   {len(cartoes)} cartão(ões) encontrado(s).")

    redacoes = listar_redacoes(PASTA_REDACOES)
    print(f"📝 {len(redacoes)} redação(ões) encontrada(s) em '{PASTA_REDACOES}'.")

    if len(redacoes) < len(cartoes):
        print(f"⚠️  Atenção: há menos redações ({len(redacoes)}) do que cartões ({len(cartoes)}).")
        print("   Os cartões sem par serão exportados sem sobreposição.")

    for i, cartao in enumerate(cartoes):
        nome_saida = saida / f"cartao_{i+1:03d}.png"

        if i < len(redacoes):
            print(f"  ✅ Cartão {i+1:03d} ← {redacoes[i].name}")
            cartao_final = sobrepor_redacao(cartao, redacoes[i], AREA_RESPOSTA)
        else:
            print(f"  ⬜ Cartão {i+1:03d} — sem redação, exportando original")
            cartao_final = cartao

        cartao_final.save(nome_saida, "PNG", dpi=(DPI, DPI))

    print(f"\n🎉 Concluído! {len(cartoes)} PNG(s) salvo(s) em '{PASTA_SAIDA}'.")


if __name__ == "__main__":
    main()
