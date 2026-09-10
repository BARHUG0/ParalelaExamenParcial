import argparse
import csv
import os
import subprocess
from pathlib import Path
from statistics import mean

RAIZ = Path(__file__).resolve().parent
FUENTE_PARALELO = RAIZ / "secuencial" / "paralela" / "riemann_openmp.c"
FUENTE_SECUENCIAL = RAIZ / "secuencial" / "riemann_secuencial.c"
INCLUDE = RAIZ / "secuencial"
SUFIX = "_problema_riemman_hugo"
EJECUTABLE_SECUENCIAL = RAIZ / "secuencial" / f"riemann_secuencial{SUFIX}.exe"
EJECUTABLE_PARALELO = RAIZ / "secuencial" / "paralela" / f"riemann_openmp{SUFIX}.exe"
DIR_RESULTADOS = RAIZ / "resultados"
ARCHIVO_RESULTADOS = DIR_RESULTADOS / f"resultados{SUFIX}.csv"
ARCHIVO_RESUMEN = DIR_RESULTADOS / f"resumen{SUFIX}.csv"

BANDERAS_BASE = ["-O3", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", f"-I{INCLUDE}"]
COLUMNAS = ["modo", "hilos", "repeticion", "tiempo"]
COLUMNAS_RESUMEN = ["modo", "hilos", "repeticiones", "tiempo_promedio", "speedup", "eficiencia"]


def compilar():
    subprocess.run(
        ["gcc"] + BANDERAS_BASE + ["-fsyntax-only", str(FUENTE_SECUENCIAL)],
        check=True,
    )
    subprocess.run(
        ["gcc"]
        + BANDERAS_BASE
        + ["-fopenmp", str(FUENTE_PARALELO), "-o", str(EJECUTABLE_PARALELO)],
        check=True,
    )
    subprocess.run(
        ["gcc"]
        + BANDERAS_BASE
        + [str(FUENTE_SECUENCIAL), "-o", str(EJECUTABLE_SECUENCIAL)],
        check=True,
    )


def ejecutar(comando):
    entorno = os.environ.copy()
    entorno["OMP_DYNAMIC"] = "FALSE"
    ejecucion = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=entorno,
        check=True,
    )

    datos = {}
    for linea in ejecucion.stdout.splitlines():
        if "=" in linea:
            clave, valor = linea.split("=", 1)
            datos[clave.strip()] = valor.strip()

    requeridas = {"modo", "hilos", "error_absoluto", "tiempo_segundos"}
    faltantes = requeridas - datos.keys()
    if faltantes:
        raise SystemExit(f"Salida incompleta de {' '.join(comando)}: {sorted(faltantes)}")

    n = int(datos["n"])
    if float(datos["error_absoluto"]) > max(1.0e-8, 1.0 / n):
        raise SystemExit(f"Error numerico inesperado: {datos}")

    modo = "paralelo" if datos["modo"] == "openmp" else datos["modo"]
    return {"modo": modo, "hilos": int(datos["hilos"]), "tiempo": float(datos["tiempo_segundos"])}


def recolectar(n, repeticiones, hilos):
    comando_secuencial = [str(EJECUTABLE_SECUENCIAL), "1", "0", "1", str(n)]
    comandos_paralelos = {
        cantidad: [str(EJECUTABLE_PARALELO), "1", "0", "1", str(n), str(cantidad)]
        for cantidad in hilos
    }

    print("Ejecutando calentamiento...")
    ejecutar(comando_secuencial)
    for comando in comandos_paralelos.values():
        ejecutar(comando)

    filas = []
    for repeticion in range(repeticiones):
        filas.append(ejecutar(comando_secuencial) | {"repeticion": repeticion})
        for comando in comandos_paralelos.values():
            filas.append(ejecutar(comando) | {"repeticion": repeticion})

    DIR_RESULTADOS.mkdir(exist_ok=True)
    with ARCHIVO_RESULTADOS.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)

    print(f"\nResultados guardados en {ARCHIVO_RESULTADOS}")


def resumir():
    with ARCHIVO_RESULTADOS.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    grupos = {}
    for fila in filas:
        clave = (fila["modo"], int(fila["hilos"]))
        grupos.setdefault(clave, []).append(float(fila["tiempo"]))

    base = mean(grupos[("secuencial", 1)])

    ordenados = sorted(
        grupos.items(),
        key=lambda item: (item[0][0] != "secuencial", item[0][1]),
    )

    resumen = []
    print(f"\n{'Modo':<12}{'Hilos':>6}{'Tiempo (s)':>14}{'Speedup':>10}{'Eficiencia':>13}")
    for (modo, hilos), tiempos in ordenados:
        promedio = mean(tiempos)
        speedup = base / promedio
        eficiencia = 100.0 * speedup / hilos
        print(f"{modo:<12}{hilos:>6}{promedio:>14.3f}{speedup:>10.2f}{eficiencia:>12.1f}%")
        resumen.append({
            "modo": modo,
            "hilos": hilos,
            "repeticiones": len(tiempos),
            "tiempo_promedio": f"{promedio:.6f}",
            "speedup": f"{speedup:.4f}",
            "eficiencia": f"{eficiencia:.2f}",
        })

    with ARCHIVO_RESUMEN.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_RESUMEN)
        escritor.writeheader()
        escritor.writerows(resumen)

    print(f"\nResumen guardado en {ARCHIVO_RESUMEN}")


def main():
    parser = argparse.ArgumentParser(description="Recolecta tiempos de la suma de Riemann y resume speedup y eficiencia")
    parser.add_argument("--resumen", action="store_true", help="Solo resume el CSV existente")
    parser.add_argument("--n", type=int, default=1_000_000_000)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--hilos", default="1,2,4,8")
    argumentos = parser.parse_args()

    if argumentos.resumen:
        resumir()
        return

    hilos = sorted({int(valor) for valor in argumentos.hilos.split(",")})
    compilar()
    recolectar(argumentos.n, argumentos.repeticiones, hilos)
    resumir()


if __name__ == "__main__":
    main()
