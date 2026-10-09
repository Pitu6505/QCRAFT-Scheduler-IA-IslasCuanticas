OPENQASM 3.0;
include "stdgates.inc";

// 25 Centinelas (5 Zonas x 5 Ventanas temporales)
qubit[25] radar;
bit[25] c_flag;

// 1. Sensibilización de las antenas (Superposición)
h radar;

// 2. Malla de Ventanas Temporales Fijas (Radar Distribuido)
// --- ZONA NORTE (Índices 0 a 4) ---
// radar[0] -> v0 (0 dt, escucha inmediata)
delay[2535dt] radar[1];  // v1
delay[5070dt] radar[2];  // v2
delay[7605dt] radar[3];  // v3
delay[10140dt] radar[4]; // v4

// --- ZONA OESTE (Índices 5 a 9) ---
delay[2535dt] radar[6];
delay[5070dt] radar[7];
delay[7605dt] radar[8];
delay[10140dt] radar[9];

// --- ZONA ESTE (Índices 10 a 14) ---
delay[2535dt] radar[11];
delay[5070dt] radar[12];
delay[7605dt] radar[13];
delay[10140dt] radar[14];

// --- ZONA CENTRO (Índices 15 a 19) ---
delay[2535dt] radar[16];
delay[5070dt] radar[17];
delay[7605dt] radar[18];
delay[10140dt] radar[19];

// --- ZONA SUR (Índices 20 a 24) ---
delay[2535dt] radar[21];
delay[5070dt] radar[22];
delay[7605dt] radar[23];
delay[10140dt] radar[24];

// 3. Muro de anclaje ALAP y Medición simultánea
barrier radar;
measure radar -> c_flag;