#!/usr/bin/env python3
"""Convierte la evidencia textual real del benchmark en una imagen legible."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CARPETA_PARALELA = Path(__file__).resolve().parent
ENTRADA = CARPETA_PARALELA / "evidencia_ejecucion.txt"
SALIDA = CARPETA_PARALELA / "evidencia_terminal.png"
FUENTES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def fuente_mono(tamano: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for ruta in FUENTES:
        if Path(ruta).is_file():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default()


def main() -> None:
    lineas = ENTRADA.read_text(encoding="utf-8").splitlines()
    fuente = fuente_mono(24)
    fuente_titulo = fuente_mono(21)
    margen_x = 46
    barra = 66
    paso = 36
    ancho = 1660
    alto = barra + 32 + len(lineas) * paso + 35

    imagen = Image.new("RGB", (ancho, alto), "#0d1117")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle(
        (1, 1, ancho - 2, alto - 2),
        radius=20,
        fill="#0d1117",
        outline="#30363d",
        width=3,
    )
    dibujo.rectangle((2, 2, ancho - 3, barra), fill="#161b22")
    for centro_x, color in (
        (34, "#ff5f57"),
        (68, "#febc2e"),
        (102, "#28c840"),
    ):
        dibujo.ellipse(
            (centro_x - 10, 23, centro_x + 10, 43), fill=color
        )

    titulo = "Evidencia real - benchmark OpenMP"
    caja = dibujo.textbbox((0, 0), titulo, font=fuente_titulo)
    dibujo.text(
        ((ancho - (caja[2] - caja[0])) / 2, 21),
        titulo,
        font=fuente_titulo,
        fill="#8b949e",
    )

    y = barra + 26
    for linea in lineas:
        color = "#7ee787" if linea.startswith("$") else "#e6edf3"
        if linea.startswith(("secuencial", "openmp")):
            color = "#a5d6ff"
        if linea.startswith("Validación"):
            color = "#f2cc60"
        dibujo.text((margen_x, y), linea, font=fuente, fill=color)
        y += paso

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(SALIDA, dpi=(180, 180), optimize=True)
    print(SALIDA)


if __name__ == "__main__":
    main()
