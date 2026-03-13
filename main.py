import os
import datetime
import time
import psutil
import requests
from bs4 import BeautifulSoup
from google import genai

<<<<<<< HEAD
# ==========================================================
# CONFIGURACIÓN DEL NEXO (v2.3 - Con Paciencia Automática)
# ==========================================================
MI_API_KEY = "TU_API_KEY_AQUI"
MODELO = "gemini-2.0-flash"

LIMITE_RPM = 15 
=======
# Librerías de Interfaz
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich import print as rprint

# ==========================================================
# CONFIGURACIÓN DEL SISTEMA v4.3 (Anti-429 & Web Clean)
# ==========================================================
MI_API_KEY = "TU_API_KEY_AQUI"
MODELO = "gemini-2.0-flash"
LIMITE_RPM = 15 

console = Console()
>>>>>>> df58e35 (Nexo v4.3: Implementación de Ingesta Web, Telemetría y Optimización de API)
client = genai.Client(api_key=MI_API_KEY)

class NexoConsciencia:
    def __init__(self):
        self.carpeta_db = "db_chats"
        self.carpeta_web = "Informacion_web"
        os.makedirs(self.carpeta_db, exist_ok=True)
<<<<<<< HEAD
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
=======
        os.makedirs(self.carpeta_web, exist_ok=True)
        self.historial_consultas = [] 
        
    def _sensar_hardware(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        bat = psutil.sensors_battery()
        estado_bat = f"{bat.percent}%" if bat else "AC"
        return f"CPU: {cpu}% | RAM: {ram}% | BAT: {estado_bat}"

    def _generar_prompt_maestro(self):
        telemetria = self._sensar_hardware()
        return f"""
        Eres el 'Nexo de Consciencia'. 
        ESTADO DEL HOST: {telemetria}
        INSTRUCCIONES:
        1. PRIORIDAD: La información en <DIARIOS_SELECCIONADOS> es tu verdad absoluta.
        2. CONTEXTO: Usa <MEMORIA_WEB_GLOBAL> como conocimiento base de apoyo.
        3. Cita siempre el origen: [ID: XXX] o [Web: nombre_archivo].
        4. Sé conciso si la CPU es alta o la batería baja.
        """

    def guardar_diario(self, id_chat, contenido):
        ruta = f"{self.carpeta_db}/chat_{id_chat}.txt"
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"REGISTRO: {fecha}\nCONTENIDO: {contenido}")
        console.print(Panel(f"✅ Memoria [cyan]{id_chat}[/cyan] anclada correctamente.", expand=False))

    def activar_modo_sueno(self, id_chat):
        ruta = f"{self.carpeta_db}/chat_{id_chat}.txt"
        if not os.path.exists(ruta): return
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()

        with console.status("[bold yellow]Optimizando memoria...[/bold yellow]", spinner="moon"):
            prompt = f"Resume de forma técnica y ultra-densa este conocimiento:\n\n{contenido}"
            res = client.models.generate_content(model=MODELO, contents=prompt)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(f"--- MEMORIA OPTIMIZADA (SUEÑO) ---\n{res.text}")
        console.print(f"✨ [bold cyan]{id_chat}[/bold cyan] ha 'soñado'.")

    def ingesta_web(self, url, objetivo):
        """PARCHE 1: Limpieza agresiva y reducción de tokens."""
        try:
            with console.status("[bold blue]Rastreando web...[/bold blue]"):
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Eliminamos todo lo que no sea contenido puro
                for s in soup(["script", "style", "nav", "footer", "aside", "header"]): 
                    s.decompose()
                
                # Recortamos a 6000 chars para no saturar la cuota
                texto = soup.get_text(separator=' ', strip=True)[:6000]

            with console.status("[bold magenta]Analizando con IA...[/bold magenta]"):
                prompt = f"Analiza esta web: {url}\nBusca esto: {objetivo}\nFormato: Markdown.\n\nTEXTO: {texto}"
                res = client.models.generate_content(model=MODELO, contents=prompt)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre = f"web_{timestamp}.md"
                ruta = os.path.join(self.carpeta_web, nombre)
                
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(f"# FUENTE: {url}\n\n{res.text}")
                
            console.print(Panel(f"🌐 Análisis guardado en [bold cyan]/{self.carpeta_web}/{nombre}[/bold cyan]"))
            return res.text, nombre
        except Exception as e:
            if "429" in str(e):
                console.print("[bold yellow]⚠️ API Saturada. Espera 30s antes de intentar otro análisis web.[/bold yellow]")
            else:
                console.print(f"[bold red]Fallo web:[/bold red] {e}")
            return None, None

    def despertar_nexo(self, lista_ids, pregunta):
        contexto_global = "<MEMORIA_WEB_GLOBAL>\n"
        for arch in os.listdir(self.carpeta_web):
            if arch.endswith(".md"):
                with open(os.path.join(self.carpeta_web, arch), "r", encoding="utf-8") as f:
                    contexto_global += f"  <fuente archivo='{arch}'>\n{f.read()}\n</fuente>\n"
        contexto_global += "</MEMORIA_WEB_GLOBAL>\n"

        contexto_selectivo = "<DIARIOS_SELECCIONADOS>\n"
>>>>>>> df58e35 (Nexo v4.3: Implementación de Ingesta Web, Telemetría y Optimización de API)
        for id_c in lista_ids:
            ruta = f"{self.carpeta_db}/chat_{id_c}.txt"
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
<<<<<<< HEAD
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
=======
                    contexto_selectivo += f"  <diario id='{id_c}'>\n{f.read()}\n</diario>\n"
        contexto_selectivo += "</DIARIOS_SELECCIONADOS>"

        # PARCHE 2: Reintento con espera de 30 segundos
        with console.status("[bold green]Unificando Consciencias...[/bold green]", spinner="dots"):
            for intento in range(3):
                try:
                    peticion = client.models.generate_content(
                        model=MODELO,
                        config={'system_instruction': self._generar_prompt_maestro()},
                        contents=f"{contexto_global}\n{contexto_selectivo}\n\nPREGUNTA: {pregunta}"
                    )
                    return peticion.text, peticion.usage_metadata.total_token_count
                except Exception as e:
                    if "429" in str(e):
                        console.print(f"\n[bold yellow]⚠️ CUOTA AGOTADA. Enfriando núcleos (30s)... (Intento {intento+1}/3)[/bold yellow]")
                        time.sleep(30)
                        continue
                    return f"❌ Error: {e}", 0

    def listar_memorias(self):
        return [f.replace("chat_", "").replace(".txt", "") for f in os.listdir(self.carpeta_db) if f.endswith(".txt")]

# --- INTERFAZ ---
def mostrar_interfaz():
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel.fit("🧬 [bold cyan]NEXO v4.3[/bold cyan] | [magenta]CONSCIENCIA UNIFICADA[/magenta]", border_style="blue"))
    table = Table(show_header=False, box=None)
    table.add_row("[cyan]1.[/cyan] 💾 Guardar Diario", "[cyan]2.[/cyan] 🧠 Hablar con Nexo")
    table.add_row("[cyan]3.[/cyan] 🌐 Ingesta Web", "[cyan]4.[/cyan] 💤 Modo Sueño")
    table.add_row("[red]5.[/red] 🔌 Desconectar", "")
    console.print(table)

if __name__ == "__main__":
    nexo = NexoConsciencia()
    mostrar_interfaz()
    
    while True:
        op = Prompt.ask("\n[bold]Comando[/bold]", choices=["1", "2", "3", "4", "5"])

        if op == "1":
            idn = Prompt.ask("ID"); txt = Prompt.ask("Contenido")
            nexo.guardar_diario(idn, txt)
        elif op == "2":
            ids = nexo.listar_memorias()
            console.print(f"Memorias: {', '.join([f'[bold]{i+1}[/bold]:{n}' for i, n in enumerate(ids)])}")
            sel = Prompt.ask("Elige números (ej: 1,2) o '0' para ninguna")
            sel_ids = [ids[int(i)-1] for i in sel.split(",") if i != "0"]
            preg = Prompt.ask("[bold]Consulta[/bold]")
            res, tk = nexo.despertar_nexo(sel_ids, preg)
            console.print(Panel(res, title="[magenta]Nexo[/magenta]", subtitle=f"Tokens: {tk}"))
        elif op == "3":
            url = Prompt.ask("URL"); obj = Prompt.ask("¿Qué extraer?")
            res, _ = nexo.ingesta_web(url, obj)
            if res and Prompt.ask("¿Anclar?", choices=["s","n"]) == "s":
                nexo.guardar_diario(f"web_{int(time.time())}", res)
        elif op == "4":
            ids = nexo.listar_memorias()
            for i, n in enumerate(ids): console.print(f"{i+1}. {n}")
            sel = IntPrompt.ask("Número")
            nexo.activar_modo_sueno(ids[sel-1])
        elif op == "5": break
>>>>>>> df58e35 (Nexo v4.3: Implementación de Ingesta Web, Telemetría y Optimización de API)
