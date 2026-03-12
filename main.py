import os
import time
from google import genai

# Tu clave API
MI_API_KEY = "INSERT_API_KEY_HERE"
client = genai.Client(api_key=MI_API_KEY)

class ChatManager:
    def __init__(self):
        self.carpeta_db = "db_chats"
        os.makedirs(self.carpeta_db, exist_ok=True)

    def guardar_dato(self, id_chat, contenido):
        ruta = f"{self.carpeta_db}/chat_{id_chat}.txt"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"💾 Memoria ID {id_chat} guardada correctamente.")

    def listar_ids(self):
        """Muestra qué chats tenemos guardados actualmente."""
        archivos = [f for f in os.listdir(self.carpeta_db) if f.endswith(".txt")]
        if not archivos:
            print("📭 La biblioteca está vacía.")
        else:
            print("\n📚 IDS DISPONIBLES EN TU BIBLIOTECA:")
            for archivo in archivos:
                # Quitamos 'chat_' y '.txt' para mostrar solo el ID
                id_limpio = archivo.replace("chat_", "").replace(".txt", "")
                print(f" - ID: {id_limpio}")

    def hablar_con_consciencia(self, lista_ids, pregunta):
        contexto = "MEMORIAS DISPONIBLES:\n"
        for id_c in lista_ids:
            ruta = f"{self.carpeta_db}/chat_{id_c}.txt"
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    contexto += f"\n[ID {id_c}]: {f.read()}\n"
        
        prompt = f"{contexto}\n\nPregunta: {pregunta}"
        
        try:
            print(f"🧠 Consultando a los IDs {lista_ids}...")
            respuesta = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
            return respuesta.text
        except Exception as e:
            if "429" in str(e):
                return "⏳ LÍMITE ALCANZADO: Google pide que esperes unos 30 segundos antes de preguntar otra vez."
            return f"❌ Error inesperado: {e}"

# --- MENÚ PRINCIPAL ---
if __name__ == "__main__":
    motor = ChatManager()
    print("--- 🧠 GESTOR DE CONSCIENCIAS v1.2 ---")
    
    while True:
        print("\n[1] Guardar Memoria | [2] Hablar con Consciencia | [3] Listar IDs | [4] Salir")
        opcion = input("Elige una opción: ")

        if opcion == "1":
            id_n = input("ID (ej: 001): ")
            texto = input("Contenido: ")
            motor.guardar_dato(id_n, texto)
        
        elif opcion == "2":
            motor.listar_ids() # Te mostramos lo que tienes antes de preguntar
            ids_input = input("\n¿Qué IDs quieres unir? (ej: 001,002): ")
            lista_ids = [i.strip() for i in ids_input.split(",")]
            pregunta = input("Tu pregunta: ")
            
            resp = motor.hablar_con_consciencia(lista_ids, pregunta)
            print("\n--- RESPUESTA ---\n" + resp)
            
        elif opcion == "3":
            motor.listar_ids()
            
        elif opcion == "4":
            print("Desconectando consciencias... ¡Hasta pronto!")
            break
