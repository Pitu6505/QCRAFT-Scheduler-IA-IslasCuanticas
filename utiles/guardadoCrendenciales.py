from qiskit_ibm_runtime import QiskitRuntimeService

# Sustituye estos valores con tu nuevo token y tu instancia (CRN) de IBM Cloud
NUEVO_TOKEN = "TU_NUEVO_TOKEN_AQUI"
INSTANCIA_CRN = "TU_INSTANCIA_CRN_AQUI"

QiskitRuntimeService.save_account(
    channel="ibm_cloud",
    token=NUEVO_TOKEN,
    instance=INSTANCIA_CRN,
    set_as_default=True,
    overwrite=True
)

print("Credenciales de IBM Cloud actualizadas y guardadas correctamente.")