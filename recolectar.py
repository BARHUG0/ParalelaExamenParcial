import argparse
import csv
import subprocess
from pathlib import Path
from statistics import mean

RAIZ = Path(__file__).resolve().parent
FUENTE_PARALELO = RAIZ / "paralelo" / "busquedaRutaMinimaParalela.c"
FUENTE_SECUENCIAL = RAIZ / "secuencial" / "busquedaRutaMinima.c"
SUFIX = "_problema_grafo"
EJECUTABLE = RAIZ / "paralelo" / f"busquedaRutaMinimaParalela{SUFIX}.exe"
DIR_RESULTADOS = RAIZ / "resultados"
ARCHIVO_RESULTADOS = DIR_RESULTADOS / f"resultados{SUFIX}.csv"
ARCHIVO_RESUMEN = DIR_RESULTADOS / f"resumen{SUFIX}.csv"

COLUMNAS = ["modo", "hilos", "repeticion", "tiempo"]
COLUMNAS_RESUMEN = ["modo", "hilos", "repeticiones", "tiempo_promedio", "speedup", "eficiencia"]


def compilar():
    subprocess.run(
        ["gcc", "-O2", "-fopenmp", str(FUENTE_PARALELO), "-o", str(EJECUTABLE)],
        check=True,
    )
    subprocess.run(["gcc", "-O2", "-fsyntax-only", str(FUENTE_SECUENCIAL)], check=True)


def recolectar(semilla, repeticiones, hilos):
    ejecucion = subprocess.run(
        [str(EJECUTABLE), str(semilla), str(repeticiones), hilos],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    filas = []
    salida_legible = []
    for linea in ejecucion.stdout.splitlines():
        partes = linea.strip().split(",")
        if partes[0] == "DATOS":
            filas.append({
                "modo": partes[1],
                "hilos": int(partes[2]),
                "repeticion": int(partes[3]),
                "tiempo": float(partes[4]),
            })
        else:
            salida_legible.append(linea)

    if not filas:
        raise SystemExit("El ejecutable no produjo lineas DATOS")

    DIR_RESULTADOS.mkdir(exist_ok=True)
    with ARCHIVO_RESULTADOS.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)

    print("\n".join(salida_legible))
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
    parser = argparse.ArgumentParser(description="Recolecta tiempos y resume speedup y eficiencia")
    parser.add_argument("--resumen", action="store_true", help="Solo resume el CSV existente")
    parser.add_argument("--semilla", type=int, default=12345)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--hilos", default="1,2,4,8")
    argumentos = parser.parse_args()

    if argumentos.resumen:
        resumir()
        return

    compilar()
    recolectar(argumentos.semilla, argumentos.repeticiones, argumentos.hilos)
    resumir()


if __name__ == "__main__":
    main()
