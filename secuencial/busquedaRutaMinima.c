#include <stdio.h>
#include <stdbool.h>

#define MAX_NODOS 1000 

int grafo[MAX_NODOS][MAX_NODOS]; 
int num_amigos[MAX_NODOS];

void encontrar_camino_mas_corto(int inicio, int destino) {
    int cola[MAX_NODOS];
    int frente = 0, final = 0;
    
    bool visitados[MAX_NODOS] = {false};
    int padre[MAX_NODOS];
    int camino[MAX_NODOS];
    int actual = -1;
    
    bool encontrado = false;

    for(int i = 0; i < MAX_NODOS; i++) {
        padre[i] = -1;
    }


    cola[final++] = inicio;
    visitados[inicio] = true;

    while (frente < final) {
        actual = cola[frente++]; 

        if (actual == destino) {
            encontrado = true;
            break;
        }

        for (int i = 0; i < num_amigos[actual]; i++) {
            int vecino = grafo[actual][i];
            
            if (!visitados[vecino]) {
                visitados[vecino] = true;
                padre[vecino] = actual;
                cola[final++] = vecino; 
            }
        }
    }

    if (encontrado) {
        int longitud = 0;
        int rastreador = destino;
        
        while (rastreador != -1) {
            camino[longitud++] = rastreador;
            rastreador = padre[rastreador];
        }

        printf("Camino más corto de %d a %d: ", inicio, destino);
        for (int i = longitud - 1; i >= 0; i--) {
            printf("%d", camino[i]);
            if (i > 0) printf(" -> ");
        }
        printf("\n");
        
    } else {
        printf("No existe conexión entre %d y %d.\n", inicio, destino);
    }
}