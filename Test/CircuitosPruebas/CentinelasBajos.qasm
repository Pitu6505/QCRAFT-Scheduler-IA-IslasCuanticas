OPENQASM 3.0;
include "stdgates.inc";

// NOTA: NO declaramos registros de qubits virtuales como 'qubit[3] q;'
bit[2] c_data;
bit[1] c_flag;

// 1. Preparación usando QUBITS FÍSICOS DIRECTOS ($)
h $13; // Forzamos al qubit físico 13 como centinela
h $11; // Forzamos al qubit físico 11 como datos
cx $11, $12; // Puerta CX física entre el qubit 11 y el 12

barrier;

// 2. Medida del centinela físico
h $13;
c_flag[0] = measure $13;

// 3. Lógica dinámica condicional
if (c_flag == 0) {
    x $11;
}

barrier;

// 4. Medidas finales en los qubits físicos asignados
c_data[0] = measure $11;
c_data[1] = measure $12;