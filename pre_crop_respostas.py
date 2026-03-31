"""
pre_crop_redacoes.py
--------------------
Faz crop nas imagens das redações, removendo:
  - Texto de apoio no topo (crop de baixo para cima)
  - Margem excessiva na parte inferior (crop de cima para baixo)

Aceita como entrada:
  - Imagens avulsas (PNG, JPG, JPEG, WEBP)
  - PDFs com múltiplas páginas (cada página vira um PNG separado)

Uso:
    python3 pre_crop_redacoes.py
    python3 pre_crop_redacoes.py --topo 0.20
    python3 pre_crop_redacoes.py --topo 0.20 --base 0.10
    python3 pre_crop_redacoes.py --topo 0.20 --base 0.10 --overlay

Dependências:
    pip install pillow pymupdf
"""

import argparse
import subprocess
from pathlib import Path

from PIL import Image
import fitz  # PyMuPDF


# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

PASTA_ENTRADA = "respostas/"       # Pasta com imagens e/ou PDFs
PASTA_SAIDA   = "respostas_crop/"  # Pasta onde os arquivos cropados serão salvos

DPI = 200  # Resolução usada ao converter páginas de PDF em imagem

# ─────────────────────────────────────────────


def aplicar_crop(img: Image.Image, cortar_topo: float, cortar_base: float) -> Image.Image:
    """Recorta a imagem removendo uma faixa do topo e/ou da base."""
    largura, altura = img.size
    y_inicio = int(altura * cortar_topo)
    y_fim    = int(altura * (1 - cortar_base))

    if y_inicio >= y_fim:
        print("  ⚠️  Os valores de --topo e --base somam 100% ou mais. Verifique os parâmetros.")
        return img

    return img.crop((0, y_inicio, largura, y_fim))


def processar_imagem(path: Path, saida: Path, cortar_topo: float, cortar_base: float) -> int:
    """Processa um único arquivo de imagem. Retorna 1 se ok."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    y_inicio = int(h * cortar_topo)
    y_fim    = int(h * (1 - cortar_base))

    img_crop = aplicar_crop(img, cortar_topo, cortar_base)
    destino  = saida / (path.stem + ".png")
    img_crop.save(destino, "PNG")

    print(f"  ✅ {path.name} → {destino.name}  (y={y_inicio}px até y={y_fim}px | altura original: {h}px)")
    return 1


def processar_pdf(path: Path, saida: Path, cortar_topo: float, cortar_base: float, dpi: int) -> int:
    """Extrai páginas do PDF, aplica crop e salva cada uma como PNG. Retorna nº de páginas."""
    doc = fitz.open(str(path))
    total = len(doc)
    print(f"  📄 {path.name} — {total} página(s) encontrada(s)")

    for i, pagina in enumerate(doc):
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = pagina.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        w, h = img.size
        y_inicio = int(h * cortar_topo)
        y_fim    = int(h * (1 - cortar_base))

        img_crop = aplicar_crop(img, cortar_topo, cortar_base)
        nome     = f"{path.stem}_pag{i+1:03d}.png"
        destino  = saida / nome
        img_crop.save(destino, "PNG")

        print(f"    ✅ Página {i+1:03d} → {nome}  (y={y_inicio}px até y={y_fim}px | altura original: {h}px)")

    doc.close()
    return total


def main():
    parser = argparse.ArgumentParser(
        description="Crop de redações: aceita imagens e PDFs, remove topo e/ou base."
    )
    parser.add_argument("--topo", type=float, default=0.0,
                        help="Percentual do topo a descartar, ex: 0.20 = 20%% (padrão: 0.0)")
    parser.add_argument("--base", type=float, default=0.0,
                        help="Percentual da base a descartar, ex: 0.10 = 10%% (padrão: 0.0)")
    parser.add_argument("--overlay", action="store_true",
                        help="Após o crop, executa o cartao_overlay.py automaticamente")
    args = parser.parse_args()

    cortar_topo = args.topo
    cortar_base = args.base

    entrada = Path(PASTA_ENTRADA)
    saida   = Path(PASTA_SAIDA)
    saida.mkdir(parents=True, exist_ok=True)

    exts_imagem = {".png", ".jpg", ".jpeg", ".webp"}
    arquivos = sorted(
        p for p in entrada.iterdir()
        if p.suffix.lower() in exts_imagem | {".pdf"}
    )

    if not arquivos:
        print(f"⚠️  Nenhuma imagem ou PDF encontrado em '{PASTA_ENTRADA}'.")
        return

    pdfs   = [p for p in arquivos if p.suffix.lower() == ".pdf"]
    imgs   = [p for p in arquivos if p.suffix.lower() in exts_imagem]

    print(f"✂️  Encontrado(s): {len(pdfs)} PDF(s) e {len(imgs)} imagem(ns)")
    print(f"   Descartando {int(cortar_topo * 100)}% do topo e {int(cortar_base * 100)}% da base\n")

    total_gerados = 0

    for pdf in pdfs:
        total_gerados += processar_pdf(pdf, saida, cortar_topo, cortar_base, DPI)

    for img in imgs:
        total_gerados += processar_imagem(img, saida, cortar_topo, cortar_base)

    print(f"\n🎉 Concluído! {total_gerados} PNG(s) salvo(s) em '{PASTA_SAIDA}'.")

    if args.overlay:
        overlay_path = Path(__file__).parent / "cartao_overlay.py"
        if not overlay_path.exists():
            print(f"\n❌ Não encontrei '{overlay_path}'. Verifique se ele está na mesma pasta.")
            return
        print(f"\n🔗 Chamando cartao_overlay.py...\n{'─' * 40}")
        subprocess.run(["python3", str(overlay_path)], check=True)


if __name__ == "__main__":
    main()