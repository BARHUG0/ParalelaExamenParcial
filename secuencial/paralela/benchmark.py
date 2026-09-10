#!/usr/bin/env python3
"""Ejecuta y documenta un benchmark reproducible de Suma de Riemann."""

from __future__ import annotations

import argparse
import csv
import os
import platform
import statistics
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PARALELA = Path(__file__).resolve().parent
SECUENCIAL = RAIZ / "secuencial" / "riemann_secuencial"
PARALELO = CARPETA_PARALELA / "riemann_openmp"
RESULTADOS = CARPETA_PARALELA
GRAFICAS = CARPETA_PARALELA
EVIDENCIA = CARPETA_PARALELA


@dataclass(frozen=True)
class Medicion:
    modo: str
    hilos: int
    repeticion: int
    n: int
    area: float
    valor_exacto: float
    error_absoluto: float
    tiempo_segundos: float


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1_000_000_000)
    parser.add_argument("--repeticiones", type=int, default=5)
    parser.add_argument("--hilos", default="1,2,4,8")
    parser.add_argument("--sin-calentamiento", action="store_true")
    args = parser.parse_args()
    if args.n <= 0 or args.repeticiones <= 0:
        parser.error("n y repeticiones deben ser mayores que cero")
    try:
        args.hilos = sorted({int(valor) for valor in args.hilos.split(",")})
    except ValueError:
        parser.error("hilos debe ser una lista como 1,2,4,8")
    if not args.hilos or args.hilos[0] <= 0:
        parser.error("todos los números de hilos deben ser positivos")
    return args


def ejecutar(comando: list[str]) -> dict[str, str]:
    entorno = os.environ.copy()
    entorno["OMP_DYNAMIC"] = "FALSE"
    proceso = subprocess.run(
        comando,
        cwd=RAIZ,
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )
    datos: dict[str, str] = {}
    for linea in proceso.stdout.splitlines():
        if "=" in linea:
            clave, valor = linea.split("=", 1)
            datos[clave.strip()] = valor.strip()
    requeridas = {
        "modo",
        "hilos",
        "n",
        "area",
        "valor_exacto",
        "error_absoluto",
        "tiempo_segundos",
    }
    faltantes = requeridas - datos.keys()
    if faltantes:
        raise RuntimeError(
            f"Salida incompleta de {' '.join(comando)}: {sorted(faltantes)}"
        )
    return datos


def medir(comando: list[str], repeticion: int) -> Medicion:
    datos = ejecutar(comando)
    medicion = Medicion(
        modo=datos["modo"],
        hilos=int(datos["hilos"]),
        repeticion=repeticion,
        n=int(datos["n"]),
        area=float(datos["area"]),
        valor_exacto=float(datos["valor_exacto"]),
        error_absoluto=float(datos["error_absoluto"]),
        tiempo_segundos=float(datos["tiempo_segundos"]),
    )
    tolerancia = max(1.0e-8, 1.0 / medicion.n)
    if medicion.error_absoluto > tolerancia:
        raise RuntimeError(f"Error numérico inesperado: {medicion}")
    return medicion


def guardar_csv(
    mediciones: list[Medicion], resumen: list[dict[str, float | int | str]]
) -> None:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with (RESULTADOS / "metricas_crudas.csv").open(
        "w", newline="", encoding="utf-8"
    ) as archivo:
        escritor = csv.DictWriter(
            archivo, fieldnames=Medicion.__dataclass_fields__.keys()
        )
        escritor.writeheader()
        for medicion in mediciones:
            escritor.writerow(medicion.__dict__)

    with (RESULTADOS / "metricas_resumen.csv").open(
        "w", newline="", encoding="utf-8"
    ) as archivo:
        campos = [
            "modo",
            "hilos",
            "mediana_segundos",
            "minimo_segundos",
            "maximo_segundos",
            "speedup",
            "eficiencia_porcentaje",
        ]
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resumen)


def crear_grafica(resumen: list[dict[str, float | int | str]]) -> None:
    import matplotlib.pyplot as plt

    paralelos = [fila for fila in resumen if fila["modo"] == "openmp"]
    hilos = [int(fila["hilos"]) for fila in paralelos]
    speedups = [float(fila["speedup"]) for fila in paralelos]
    eficiencias = [float(fila["eficiencia_porcentaje"]) for fila in paralelos]

    plt.style.use("seaborn-v0_8-whitegrid")
    figura, ejes = plt.subplots(
        1, 2, figsize=(11, 4.5), constrained_layout=True
    )
    figura.suptitle("Suma de Riemann con OpenMP", fontsize=16, fontweight="bold")

    ejes[0].plot(hilos, hilos, "--", color="#9aa4ad", label="Ideal")
    ejes[0].plot(
        hilos,
        speedups,
        "o-",
        color="#176b87",
        linewidth=2.3,
        label="Medido",
    )
    ejes[0].set(title="Speedup", xlabel="Hilos", ylabel="Aceleración")
    ejes[0].set_xticks(hilos)
    ejes[0].legend()

    ejes[1].axhline(100, linestyle="--", color="#9aa4ad", label="Ideal")
    ejes[1].plot(
        hilos,
        eficiencias,
        "o-",
        color="#2f855a",
        linewidth=2.3,
        label="Medida",
    )
    ejes[1].set(title="Eficiencia", xlabel="Hilos", ylabel="Porcentaje")
    ejes[1].set_xticks(hilos)
    ejes[1].set_ylim(0, max(110, max(eficiencias) * 1.12))
    ejes[1].legend()

    GRAFICAS.mkdir(parents=True, exist_ok=True)
    figura.savefig(GRAFICAS / "riemann_speedup_eficiencia.png", dpi=180)
    plt.close(figura)


def info_cpu() -> str:
    if platform.system() == "Darwin":
        try:
            return subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return platform.processor() or platform.machine()


def version_compilador() -> str:
    try:
        salida = subprocess.check_output(
            ["make", "--no-print-directory", "compiler"], cwd=RAIZ, text=True
        )
        lineas = [
            linea
            for linea in salida.splitlines()
            if linea and not linea.startswith("/")
        ]
        return lineas[0] if lineas else "No disponible"
    except (OSError, subprocess.CalledProcessError):
        return "No disponible"


def guardar_evidencia(
    args: argparse.Namespace, resumen: list[dict[str, float | int | str]]
) -> None:
    EVIDENCIA.mkdir(parents=True, exist_ok=True)
    tolerancia = max(1.0e-8, 1.0 / args.n)
    lineas = [
        "$ make benchmark",
        "Benchmark reproducible - Suma de Riemann",
        f"Fecha: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Equipo: {info_cpu()} ({os.cpu_count()} CPU lógicas)",
        f"Compilador: {version_compilador()}",
        f"Datos: f(x)=x^2, [0,1], n={args.n}, repeticiones={args.repeticiones}",
        "",
        "Modo       Hilos   Mediana(s)   Speedup   Eficiencia",
        "----------------------------------------------------",
    ]
    for fila in resumen:
        lineas.append(
            f"{str(fila['modo']):<11} {int(fila['hilos']):>5}   "
            f"{float(fila['mediana_segundos']):>10.6f}   "
            f"{float(fila['speedup']):>7.3f}   "
            f"{float(fila['eficiencia_porcentaje']):>9.2f}%"
        )
    lineas.extend(
        [
            "",
            f"Validación: todas las corridas tuvieron error absoluto <= {tolerancia:.0e}.",
            "Archivos: paralela/metricas_crudas.csv",
            "          paralela/metricas_resumen.csv",
        ]
    )
    contenido = "\n".join(lineas) + "\n"
    (EVIDENCIA / "evidencia_ejecucion.txt").write_text(
        contenido, encoding="utf-8"
    )
    print(contenido, end="")


def main() -> None:
    args = argumentos()
    for ejecutable in (SECUENCIAL, PARALELO):
        if not ejecutable.is_file():
            raise SystemExit(f"Falta {ejecutable}; ejecute make primero")

    base = [str(SECUENCIAL), "1", "0", "1", str(args.n)]
    comandos_paralelos = {
        hilos: [str(PARALELO), "1", "0", "1", str(args.n), str(hilos)]
        for hilos in args.hilos
    }

    if not args.sin_calentamiento:
        ejecutar(base)
        for comando in comandos_paralelos.values():
            ejecutar(comando)

    mediciones: list[Medicion] = []
    for repeticion in range(1, args.repeticiones + 1):
        mediciones.append(medir(base, repeticion))
        for comando in comandos_paralelos.values():
            mediciones.append(medir(comando, repeticion))

    tiempo_base = statistics.median(
        m.tiempo_segundos for m in mediciones if m.modo == "secuencial"
    )
    configuraciones: list[tuple[str, int]] = [("secuencial", 1)] + [
        ("openmp", hilos) for hilos in args.hilos
    ]
    resumen: list[dict[str, float | int | str]] = []
    for modo, hilos in configuraciones:
        tiempos = [
            m.tiempo_segundos
            for m in mediciones
            if m.modo == modo and m.hilos == hilos
        ]
        mediana = statistics.median(tiempos)
        speedup = tiempo_base / mediana
        resumen.append(
            {
                "modo": modo,
                "hilos": hilos,
                "mediana_segundos": f"{mediana:.9f}",
                "minimo_segundos": f"{min(tiempos):.9f}",
                "maximo_segundos": f"{max(tiempos):.9f}",
                "speedup": f"{speedup:.6f}",
                "eficiencia_porcentaje": f"{speedup / hilos * 100.0:.4f}",
            }
        )

    guardar_csv(mediciones, resumen)
    crear_grafica(resumen)
    guardar_evidencia(args, resumen)


if __name__ == "__main__":
    main()
