#ifndef RIEMANN_COMUN_H
#define RIEMANN_COMUN_H

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define OPCION_MINIMA 1
#define OPCION_MAXIMA 5

typedef double (*Funcion)(double);

static double funcion_cuadrado(double x)
{
    return x * x;
}

static double funcion_exponencial(double x)
{
    return exp(x);
}

static double funcion_seno(double x)
{
    return sin(x);
}

static double funcion_coseno(double x)
{
    return cos(x);
}

static double funcion_raiz(double x)
{
    return sqrt(x);
}

static const Funcion TABLA_FUNCIONES[] = {
    NULL,
    funcion_cuadrado,
    funcion_exponencial,
    funcion_seno,
    funcion_coseno,
    funcion_raiz,
};

static const char *NOMBRES_FUNCIONES[] = {
    NULL,
    "f(x) = x^2",
    "f(x) = e^x",
    "f(x) = sen(x)",
    "f(x) = cos(x)",
    "f(x) = raiz_cuadrada(x)",
};

static const char *nombre_funcion(int opcion)
{
    if (opcion < OPCION_MINIMA || opcion > OPCION_MAXIMA) {
        return "funcion_invalida";
    }
    return NOMBRES_FUNCIONES[opcion];
}

static void imprimir_menu(void)
{
    puts("Funciones disponibles:");
    for (int opcion = OPCION_MINIMA; opcion <= OPCION_MAXIMA; ++opcion) {
        printf("  %d. %s\n", opcion, NOMBRES_FUNCIONES[opcion]);
    }
}

static double evaluar_funcion(double x, int opcion)
{
    return TABLA_FUNCIONES[opcion](x);
}

static double integral_exacta(double a, double b, int opcion)
{
    switch (opcion) {
    case 1:
        return (pow(b, 3.0) - pow(a, 3.0)) / 3.0;
    case 2:
        return exp(b) - exp(a);
    case 3:
        return cos(a) - cos(b);
    case 4:
        return sin(b) - sin(a);
    case 5:
        return (2.0 / 3.0) * (pow(b, 1.5) - pow(a, 1.5));
    default:
        return NAN;
    }
}

static int validar_parametros(int opcion, double a, double b, uint64_t n)
{
    if (opcion < OPCION_MINIMA || opcion > OPCION_MAXIMA) {
        fputs("Error: funcion fuera de rango.\n", stderr);
        return 0;
    }
    if (!(b > a)) {
        fputs("Error: B debe ser mayor que A.\n", stderr);
        return 0;
    }
    if (n == 0) {
        fputs("Error: N debe ser mayor que cero.\n", stderr);
        return 0;
    }
    if (opcion == 5 && a < 0.0) {
        fputs("Error: la raiz cuadrada requiere A >= 0.\n", stderr);
        return 0;
    }
    return 1;
}

static int convertir_entero(const char *texto, long minimo, long maximo,
                            long *destino)
{
    char *fin = NULL;
    errno = 0;
    const long valor = strtol(texto, &fin, 10);
    if (errno != 0 || fin == texto || *fin != '\0' || valor < minimo ||
        valor > maximo) {
        return 0;
    }
    *destino = valor;
    return 1;
}

static int convertir_real(const char *texto, double *destino)
{
    char *fin = NULL;
    errno = 0;
    const double valor = strtod(texto, &fin);
    if (errno != 0 || fin == texto || *fin != '\0') {
        return 0;
    }
    *destino = valor;
    return 1;
}

static int convertir_n(const char *texto, uint64_t *destino)
{
    char *fin = NULL;
    errno = 0;
    const unsigned long long valor = strtoull(texto, &fin, 10);
    if (errno != 0 || fin == texto || *fin != '\0' || valor == 0) {
        return 0;
    }
    *destino = (uint64_t)valor;
    return 1;
}

static double tiempo_monotono(void)
{
    struct timespec marca;
    timespec_get(&marca, TIME_UTC);
    return (double)marca.tv_sec + (double)marca.tv_nsec / 1.0e9;
}

#endif
