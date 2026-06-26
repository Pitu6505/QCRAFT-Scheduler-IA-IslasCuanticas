OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
bit[2] c_data;
bit[1] c_flag;

// 1. Preparación en alta sensibilidad
h q[2];

// 2. Circuito de datos: Inyección masiva de pulsos de microondas (Crosstalk)
h q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];

// BARRERA 1: Evita que el compilador adelante las medidas
barrier; 

// 3. Revertimos el centinela y lo medimos
h q[2];
c_flag[0] = measure q[2];

// 4. LÓGICA DINÁMICA: Si hubo ruido (c_flag es 1), la QPU NO ejecutará esta X
if (c_flag == 0) {
    x q[0];
}

// BARRERA 2: Espera a que termine la lógica para medir los datos
barrier; 

// 5. Medidas finales (obligatoriamente al final)
c_data[0] = measure q[0];
c_data[1] = measure q[1];