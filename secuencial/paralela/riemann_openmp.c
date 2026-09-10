#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <limits.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>

#include "riemann_comun.h"

#define N_PREDETERMINADO UINT64_C(1000000000)

static double suma_riemann_openmp(double a, double ancho, uint64_t n,
                                  int opcion)
{
    double suma_areas = 0.0;

    /*
     * Cada iteración calcula un rectángulo independiente. La reducción crea
     * un acumulador privado por hilo y combina los parciales al terminar;
     * así se evita la carrera sobre suma_areas sin serializar el ciclo.
     * El reparto estático es adecuado porque todas las iteraciones cuestan
     * prácticamente lo mismo.
     */
#pragma omp parallel for default(none) shared(a, ancho, n, opcion) \
    reduction(+ : suma_areas) schedule(static)
    for (uint64_t i = 0; i < n; ++i) {
        const double x = a + (double)i * ancho;
        const double y = evaluar_funcion(x, opcion);
        suma_areas += y * ancho;
    }

    return suma_areas;
}

static int leer_interactivo(int *opcion, double *a, double *b, uint64_t *n,
                            int *hilos)
{
    imprimir_menu();
    printf("Seleccione una función: ");
    if (scanf("%d", opcion) != 1) {
        return 0;
    }
    printf("Ingrese el límite inferior A: ");
    if (scanf("%lf", a) != 1) {
        return 0;
    }
    printf("Ingrese el límite superior B: ");
    if (scanf("%lf", b) != 1) {
        return 0;
    }
    *n = N_PREDETERMINADO;
    printf("Se usarán %" PRIu64 " rectángulos.\n", *n);
    printf("Número de hilos: ");
    if (scanf("%d", hilos) != 1) {
        return 0;
    }
    return 1;
}

static int leer_argumentos(int argc, char **argv, int *opcion, double *a,
                           double *b, uint64_t *n, int *hilos)
{
    if (argc == 1) {
        return leer_interactivo(opcion, a, b, n, hilos);
    }
    if (argc != 6) {
        fprintf(stderr, "Uso: %s FUNCION A B N HILOS\n", argv[0]);
        return 0;
    }

    long opcion_larga = 0;
    long hilos_largo = 0;
    if (!convertir_entero(argv[1], 1, 5, &opcion_larga) ||
        !convertir_real(argv[2], a) || !convertir_real(argv[3], b) ||
        !convertir_n(argv[4], n) ||
        !convertir_entero(argv[5], 1, INT_MAX, &hilos_largo)) {
        fputs("Error: argumentos inválidos.\n", stderr);
        return 0;
    }
    *opcion = (int)opcion_larga;
    *hilos = (int)hilos_largo;
    return 1;
}

int main(int argc, char **argv)
{
    int opcion = 0;
    double a = 0.0;
    double b = 0.0;
    uint64_t n = N_PREDETERMINADO;
    int hilos = 0;

    if (!leer_argumentos(argc, argv, &opcion, &a, &b, &n, &hilos) ||
        !validar_parametros(opcion, a, b, n) || hilos < 1) {
        return EXIT_FAILURE;
    }

    omp_set_dynamic(0);
    omp_set_num_threads(hilos);

    const double ancho = (b - a) / (double)n;
    const double inicio = omp_get_wtime();
    const double area = suma_riemann_openmp(a, ancho, n, opcion);
    const double tiempo = omp_get_wtime() - inicio;
    const double exacta = integral_exacta(a, b, opcion);

    puts("\n--- Resultado ---");
    puts("modo=openmp");
    printf("funcion=%s\n", nombre_funcion(opcion));
    printf("a=%.17g\n", a);
    printf("b=%.17g\n", b);
    printf("n=%" PRIu64 "\n", n);
    printf("hilos=%d\n", hilos);
    printf("area=%.15f\n", area);
    printf("valor_exacto=%.15f\n", exacta);
    printf("error_absoluto=%.15e\n", fabs(area - exacta));
    printf("tiempo_segundos=%.9f\n", tiempo);

    return EXIT_SUCCESS;
}
