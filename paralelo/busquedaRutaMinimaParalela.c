#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define NUM_NODOS 1000000
#define ARISTAS_POR_NODO 3
#define NUM_HUBS 300
#define AMIGOS_HUB 10000
#define NUM_CONSULTAS 50
#define CHUNK_ARISTAS 256
#define SEMILLA 12345

typedef struct {
    int *offsets;
    int *aristas;
} Grafo;

typedef struct {
    int nodo;
    int inicio;
    int fin;
} Tarea;

static unsigned int semilla = SEMILLA;

static unsigned int siguiente_aleatorio(void) {
    semilla ^= semilla << 13;
    semilla ^= semilla >> 17;
    semilla ^= semilla << 5;
    return semilla;
}

static void generar_grafo(Grafo *g) {
    int num_pares = NUM_NODOS * ARISTAS_POR_NODO + NUM_HUBS * AMIGOS_HUB;
    int *u = malloc(num_pares * sizeof(int));
    int *v = malloc(num_pares * sizeof(int));
    int *grados = calloc(NUM_NODOS, sizeof(int));

    int p = 0;
    for (int i = 0; i < NUM_NODOS; i++) {
        for (int k = 0; k < ARISTAS_POR_NODO; k++) {
            int j = (int)(siguiente_aleatorio() % NUM_NODOS);
            if (j == i) j = (i + 1) % NUM_NODOS;
            u[p] = i;
            v[p] = j;
            p++;
        }
    }
    for (int h = 0; h < NUM_HUBS; h++) {
        int hub = (int)(siguiente_aleatorio() % NUM_NODOS);
        for (int k = 0; k < AMIGOS_HUB; k++) {
            int j = (int)(siguiente_aleatorio() % NUM_NODOS);
            if (j == hub) j = (hub + 1) % NUM_NODOS;
            u[p] = hub;
            v[p] = j;
            p++;
        }
    }

    for (int e = 0; e < num_pares; e++) {
        grados[u[e]]++;
        grados[v[e]]++;
    }

    g->offsets = malloc((NUM_NODOS + 1) * sizeof(int));
    g->offsets[0] = 0;
    for (int i = 0; i < NUM_NODOS; i++) {
        g->offsets[i + 1] = g->offsets[i] + grados[i];
    }

    g->aristas = malloc(2 * num_pares * sizeof(int));
    int *cursor = malloc(NUM_NODOS * sizeof(int));
    for (int i = 0; i < NUM_NODOS; i++) cursor[i] = g->offsets[i];
    for (int e = 0; e < num_pares; e++) {
        g->aristas[cursor[u[e]]++] = v[e];
        g->aristas[cursor[v[e]]++] = u[e];
    }

    free(u);
    free(v);
    free(grados);
    free(cursor);
}

static int bfs_secuencial(const Grafo *g, int inicio, int destino, int *padre, int *visitados, int *cola) {
    int frente = 0, final = 0;

    cola[final++] = inicio;
    visitados[inicio] = 1;
    padre[inicio] = -1;

    while (frente < final) {
        int actual = cola[frente++];

        if (actual == destino) return 1;

        for (int e = g->offsets[actual]; e < g->offsets[actual + 1]; e++) {
            int vecino = g->aristas[e];
            if (!visitados[vecino]) {
                visitados[vecino] = 1;
                padre[vecino] = actual;
                cola[final++] = vecino;
            }
        }
    }
    return 0;
}

static int bfs_paralelo(const Grafo *g, int inicio, int destino, int *padre, int *visitados,
                        int *frontera, int *siguiente, Tarea *tareas, int **buf_locales, int num_hilos) {
    int tam_frontera = 1;
    int n_siguiente = 0;
    int n_tareas = 0;
    int encontrado = (inicio == destino);

    frontera[0] = inicio;
    visitados[inicio] = 1;
    padre[inicio] = -1;

    #pragma omp parallel num_threads(num_hilos)
    {
        int *mi_buffer = buf_locales[omp_get_thread_num()];

        while (!encontrado) {
            int n_locales = 0;

            #pragma omp single
            {
                n_tareas = 0;
                for (int j = 0; j < tam_frontera; j++) {
                    int nodo = frontera[j];
                    int fin_nodo = g->offsets[nodo + 1];
                    for (int e = g->offsets[nodo]; e < fin_nodo; e += CHUNK_ARISTAS) {
                        int fin_bloque = (e + CHUNK_ARISTAS < fin_nodo) ? e + CHUNK_ARISTAS : fin_nodo;
                        tareas[n_tareas].nodo = nodo;
                        tareas[n_tareas].inicio = e;
                        tareas[n_tareas].fin = fin_bloque;
                        n_tareas++;
                    }
                }
            }

            #pragma omp for schedule(dynamic, 1)
            for (int t = 0; t < n_tareas; t++) {
                int nodo = tareas[t].nodo;
                for (int e = tareas[t].inicio; e < tareas[t].fin; e++) {
                    int vecino = g->aristas[e];
                    int previo;
                    #pragma omp atomic capture
                    previo = visitados[vecino]++;
                    if (previo == 0) {
                        padre[vecino] = nodo;
                        mi_buffer[n_locales++] = vecino;
                    }
                }
            }

            #pragma omp critical
            {
                for (int k = 0; k < n_locales; k++) {
                    siguiente[n_siguiente++] = mi_buffer[k];
                }
            }

            #pragma omp barrier

            #pragma omp single
            {
                int *tmp = frontera;
                frontera = siguiente;
                siguiente = tmp;
                tam_frontera = n_siguiente;
                n_siguiente = 0;
                encontrado = visitados[destino] || tam_frontera == 0;
            }
        }
    }

    return encontrado;
}

static int reconstruir_camino(const int *padre, int destino, int *camino) {
    int longitud = 0;
    int actual = destino;

    while (actual != -1) {
        camino[longitud++] = actual;
        actual = padre[actual];
    }
    for (int i = 0; i < longitud / 2; i++) {
        int tmp = camino[i];
        camino[i] = camino[longitud - 1 - i];
        camino[longitud - 1 - i] = tmp;
    }
    return longitud;
}

static void imprimir_camino(const int *camino, int longitud) {
    for (int i = 0; i < longitud; i++) {
        printf("%d", camino[i]);
        if (i < longitud - 1) printf(" -> ");
    }
    printf("\n");
}

int main(void) {
    Grafo g;
    int max_hilos = omp_get_max_threads();
    int hilos_prueba[] = {1, 2, 4, 8};

    generar_grafo(&g);

    int aristas_dirigidas = g.offsets[NUM_NODOS];
    int grado_maximo = 0;
    for (int i = 0; i < NUM_NODOS; i++) {
        int grado = g.offsets[i + 1] - g.offsets[i];
        if (grado > grado_maximo) grado_maximo = grado;
    }
    printf("Grafo: %d nodos, %d aristas dirigidas, grado maximo %d\n", NUM_NODOS, aristas_dirigidas, grado_maximo);
    printf("Consultas: %d pares de usuarios conectados\n", NUM_CONSULTAS);

    int *padre = malloc(NUM_NODOS * sizeof(int));
    int *visitados = malloc(NUM_NODOS * sizeof(int));
    int *cola = malloc(NUM_NODOS * sizeof(int));
    int *camino = malloc(NUM_NODOS * sizeof(int));
    int *camino_par = malloc(NUM_NODOS * sizeof(int));
    int *frontera = malloc(NUM_NODOS * sizeof(int));
    int *siguiente = malloc(NUM_NODOS * sizeof(int));
    int max_tareas = 2 * NUM_NODOS + aristas_dirigidas / CHUNK_ARISTAS + 1;
    Tarea *tareas = malloc(max_tareas * sizeof(Tarea));
    int **buf_locales = malloc(max_hilos * sizeof(int *));
    for (int t = 0; t < max_hilos; t++) buf_locales[t] = malloc(NUM_NODOS * sizeof(int));

    int consultas[NUM_CONSULTAS][2];
    int longitudes_seq[NUM_CONSULTAS];
    int longitudes_par[NUM_CONSULTAS];
    int generadas = 0;
    while (generadas < NUM_CONSULTAS) {
        int x = (int)(siguiente_aleatorio() % NUM_NODOS);
        int y = (int)(siguiente_aleatorio() % NUM_NODOS);
        if (x == y) continue;
        memset(visitados, 0, NUM_NODOS * sizeof(int));
        if (bfs_secuencial(&g, x, y, padre, visitados, cola)) {
            consultas[generadas][0] = x;
            consultas[generadas][1] = y;
            generadas++;
        }
    }

    double t0, t1, tiempo_seq, tiempo_par;

    t0 = omp_get_wtime();
    for (int q = 0; q < NUM_CONSULTAS; q++) {
        memset(visitados, 0, NUM_NODOS * sizeof(int));
        bfs_secuencial(&g, consultas[q][0], consultas[q][1], padre, visitados, cola);
        longitudes_seq[q] = reconstruir_camino(padre, consultas[q][1], camino);
    }
    t1 = omp_get_wtime();
    tiempo_seq = t1 - t0;

    printf("\nCamino de ejemplo de %d a %d: ", consultas[NUM_CONSULTAS - 1][0], consultas[NUM_CONSULTAS - 1][1]);
    imprimir_camino(camino, longitudes_seq[NUM_CONSULTAS - 1]);

    int errores = 0;
    printf("\n%-8s %-14s %-10s %-12s\n", "Hilos", "Tiempo (s)", "Speedup", "Eficiencia");
    printf("%-8d %-14.3f %-10.2f %-11.1f%%\n", 1, tiempo_seq, 1.0, 100.0);

    for (int c = 0; c < 4; c++) {
        int h = hilos_prueba[c];
        if (h > max_hilos) continue;

        t0 = omp_get_wtime();
        for (int q = 0; q < NUM_CONSULTAS; q++) {
            memset(visitados, 0, NUM_NODOS * sizeof(int));
            int hallado = bfs_paralelo(&g, consultas[q][0], consultas[q][1], padre, visitados,
                                       frontera, siguiente, tareas, buf_locales, h);
            if (hallado) {
                longitudes_par[q] = reconstruir_camino(padre, consultas[q][1], camino_par);
            } else {
                longitudes_par[q] = 0;
            }
            if (longitudes_par[q] != longitudes_seq[q]) errores++;
        }
        t1 = omp_get_wtime();
        tiempo_par = t1 - t0;

        double speedup = tiempo_seq / tiempo_par;
        printf("%-8d %-14.3f %-10.2f %-11.1f%%\n", h, tiempo_par, speedup, 100.0 * speedup / h);
    }

    printf("\nVerificacion: %d diferencias de longitud entre las dos versiones\n", errores);

    for (int t = 0; t < max_hilos; t++) free(buf_locales[t]);
    free(buf_locales);
    free(tareas);
    free(frontera);
    free(siguiente);
    free(camino);
    free(camino_par);
    free(cola);
    free(visitados);
    free(padre);
    free(g.offsets);
    free(g.aristas);
    return 0;
}
