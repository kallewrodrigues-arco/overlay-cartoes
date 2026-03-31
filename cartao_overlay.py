"""
cartao_overlay.py
-----------------
Extrai páginas de um PDF de cartões resposta, sobrepõe imagens de respostas
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
PASTA_RESPOSTAS = "respostas/"            # Pasta com PNGs/JPEGs das respostas
PASTA_SAIDA    = "cartoes_finais/"        # Onde os PNGs finais serão salvos

# Região de resposta em percentual da página (0.0 a 1.0)
# Ajuste olhando o cartão: top_pct = onde o cabeçalho termina
AREA_RESPOSTA = {
    "left_pct":   0.03,
    "top_pct":    0.30,
    "right_pct":  0.97,
    "bottom_pct": 0.97,
}

DPI = 200

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


def listar_respostas(pasta: str) -> list[Path]:
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


def sobrepor_resposta(cartao: Image.Image, resposta_path: Path, area: dict) -> Image.Image:
    """Cola a imagem da resposta na área de resposta do cartão."""
    resultado = cartao.copy()
    largura, altura = cartao.size

    x0, y0, x1, y1 = calcular_area_px(largura, altura, area)
    area_largura = x1 - x0
    area_altura  = y1 - y0

    resposta = Image.open(resposta_path).convert("RGB")

    ratio = max(area_largura / resposta.width, area_altura / resposta.height)
    novo_w = int(resposta.width  * ratio)
    novo_h = int(resposta.height * ratio)
    resposta = resposta.resize((novo_w, novo_h), Image.LANCZOS)

    crop_x = (novo_w - area_largura) // 2
    crop_y = (novo_h - area_altura)  // 2
    resposta = resposta.crop((crop_x, crop_y, crop_x + area_largura, crop_y + area_altura))

    resultado.paste(resposta, (x0, y0))
    return resultado


def main():
    saida = Path(PASTA_SAIDA)
    saida.mkdir(parents=True, exist_ok=True)

    print(f"📄 Extraindo páginas de '{PDF_CARTOES}'...")
    cartoes = pdf_para_imagens(PDF_CARTOES, DPI)
    print(f"   {len(cartoes)} cartão(ões) encontrado(s).")

    respostas = listar_respostas(PASTA_RESPOSTAS)
    print(f"📝 {len(respostas)} resposta(s) encontrada(s) em '{PASTA_RESPOSTAS}'.")

    if len(respostas) < len(cartoes):
        print(f"⚠️  Atenção: há menos respostas ({len(respostas)}) do que cartões ({len(cartoes)}).")
        print("   Os cartões sem par serão exportados sem sobreposição.")

    for i, cartao in enumerate(cartoes):
        nome_saida = saida / f"cartao_{i+1:03d}.png"

        if i < len(respostas):
            print(f"  ✅ Cartão {i+1:03d} ← {respostas[i].name}")
            cartao_final = sobrepor_resposta(cartao, respostas[i], AREA_RESPOSTA)
        else:
            print(f"  ⬜ Cartão {i+1:03d} — sem resposta, exportando original")
            cartao_final = cartao

        cartao_final.save(nome_saida, "PNG", dpi=(DPI, DPI))

    print(f"\n🎉 Concluído! {len(cartoes)} PNG(s) salvo(s) em '{PASTA_SAIDA}'.")


if __name__ == "__main__":
    main()
