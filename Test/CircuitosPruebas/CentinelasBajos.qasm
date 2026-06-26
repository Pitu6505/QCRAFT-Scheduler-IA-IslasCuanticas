OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
bit[2] c_data;
bit[1] c_flag;

// 1. Preparación y entrelazamiento
h q[2];
h q[0];
cx q[0], q[1];

// BARRERA 1: Evita que el compilador adelante las medidas finales
barrier; 

// 2. Medida del centinela
h q[2];
c_flag[0] = measure q[2];

// 3. Lógica dinámica
if (c_flag == 0) {
    x q[0];
}

// BARRERA 2: Espera a que termine la lógica para medir los datos
barrier; 

// 4. Medidas finales (ahora sí, obligatoriamente al final)
c_data[0] = measure q[0];
c_data[1] = measure q[1];