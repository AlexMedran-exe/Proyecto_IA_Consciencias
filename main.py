import os
import datetime
import time
from google import genai

# ==========================================================
# CONFIGURACIÓN DEL NEXO (v2.3 - Con Paciencia Automática)
# ==========================================================
MI_API_KEY = "TU_API_KEY_AQUI"
MODELO = "gemini-2.0-flash"

LIMITE_RPM = 15 
client = genai.Client(api_key=MI_API_KEY)

class NexoConsciencia:
    def __init__(self):
        self.carpeta_db = "db_chats"
        os.makedirs(self.carpeta_db, exist_ok=True)
        self.historial_consultas = [] 
        
        self.system_prompt = """
        Eres el 'Nexo de Consciencia', un sistema avanzado de orquestación de memoria.
        REGLAS DE ORO:
        - Si la respuesta está en los diarios, cítalos usando su ID: [ID: XXX].
        - PRIORIDAD: Si un diario contradice tu conocimiento general, el diario manda.
        - PREVENCIÓN: No inventes fechas o hechos personales que no estén en el XML.
        """

    def _controlar_cuota(self):
        ahora = time.time()
        self.historial_consultas = [t for t in self.historial_consultas if ahora - t < 60]
        return len(self.historial_consultas) < LIMITE_RPM

    def guardar_diario(self, id_chat, contenido):
        ruta = f"{self.carpeta_db}/chat_{id_chat}.txt"
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entrada_completa = f"REGISTRO_TEMPORAL: {fecha_actual}\nCONTENIDO: {contenido}"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(entrada_completa)
        print(f"✅ Memoria [ID {id_chat}] anclada correctamente.")

    def despertar_nexo(self, lista_ids, pregunta):
        if not self._controlar_cuota():
            return "⚠️ FRENO DE SEGURIDAD: Límite local excedido. Espera 30 segundos."

        contexto_xml = "<MODULOS_DE_MEMORIA>\n"
        diarios_cargados = 0
        for id_c in lista_ids:
            ruta = f"{self.carpeta_db}/chat_{id_c}.txt"
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    contexto_xml += f"  <diario id='{id_c}'>\n    {f.read()}\n  </diario>\n"
                    diarios_cargados += 1
        contexto_xml += "</MODULOS_DE_MEMORIA>"

        # --- LÓGICA DE REINTENTO (BACKOFF) ---
        intentos_maximos = 3
        for intento in range(intentos_maximos):
            try:
                if intento > 0:
                    print(f"⏳ Reintentando conexión (Intento {intento + 1}/{intentos_maximos})...")
                
                peticion = client.models.generate_content(
                    model=MODELO,
                    config={'system_instruction': self.system_prompt},
                    contents=f"{contexto_xml}\n\nSOLICITUD: {pregunta}"
                )
                
                # Si llegamos aquí, la petición fue exitosa
                self.historial_consultas.append(time.time())
                tokens = peticion.usage_metadata.total_token_count
                info_cuota = f"\n\n[📊 Centinela: {tokens} tokens usados | Consultas/min: {len(self.historial_consultas)}/{LIMITE_RPM}]"
                return peticion.text + info_cuota

            except Exception as e:
                # Si el error es por saturación (429) y nos quedan intentos...
                if "429" in str(e) and intento < intentos_maximos - 1:
                    print(f"⚠️ Servidor saturado. El Nexo esperará 10 segundos para reintentar automáticamente...")
                    time.sleep(10)  # Pausa de seguridad
                    continue 
                else:
                    # Si es otro error o agotamos intentos, mostramos el fallo
                    return f"❌ Error tras varios intentos: {e}"

    def auditoria_identidad(self):
        archivos = [f.replace("chat_", "").replace(".txt", "") for f in os.listdir(self.carpeta_db) if f.endswith(".txt")]
        if not archivos: return "Biblioteca vacía."
        return self.despertar_nexo(archivos, "¿Quién soy yo basado en estos diarios? Describe mi perfil.")

if __name__ == "__main__":
    motor = NexoConsciencia()
    print("--- 🧠 SISTEMA NEXO DE CONSCIENCIA v2.3 ---")
    
    while True:
        print("\n" + "—"*50)
        print("[1] Guardar Memoria | [2] Consultar al Nexo | [3] Auditoría Global | [4] Salir")
        op = input("Selecciona acción: ")

        if op == "1":
            id_n = input("ID del diario (o 'q' para volver): ")
            if id_n.lower() == 'q': continue
            texto = input("Contenido (o 'q' para volver): ")
            if texto.lower() == 'q': continue
            motor.guardar_diario(id_n, texto)
        
        elif op == "2":
            archivos = [f.replace("chat_", "").replace(".txt", "") for f in os.listdir("db_chats") if f.endswith(".txt")]
            print(f"IDs disponibles: {archivos}")
            ids_input = input("IDs a fusionar (ej: 001,002) o 'q' para volver: ")
            if ids_input.lower() == 'q': continue
            
            lista_ids = [i.strip() for i in ids_input.split(",")]
            preg = input("Tu pregunta (o 'q' para volver): ")
            if preg.lower() == 'q': continue
            
            print("\n" + "="*20 + " RESPUESTA " + "="*20)
            print(motor.despertar_nexo(lista_ids, preg))
            
        elif op == "3":
            confirmar = input("¿Ejecutar auditoría completa? (s/n): ")
            if confirmar.lower() != 's': continue
            print("\n" + "="*20 + " AUDITORÍA GLOBAL " + "="*20)
            print(motor.auditoria_identidad())
            
        elif op == "4":
            print("Cerrando Nexo. Sistemas en reposo.")
            break