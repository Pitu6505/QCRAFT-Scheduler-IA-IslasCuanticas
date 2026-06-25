OPENQASM 3.0;
include "stdgates.inc";

// Declaración de 2 qubits físicos y 2 bits clásicos
qubit[2] q;
bit[2] c;

// Entrelazamiento básico
h q[0];
cx q[0], q[1];

// Medidas
c[0] = measure q[0];
c[1] = measure q[1];