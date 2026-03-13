import os
import datetime
import time
import psutil
import requests
from bs4 import BeautifulSoup
from google import genai

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
client = genai.Client(api_key=MI_API_KEY)

class NexoConsciencia:
    def __init__(self):
        self.carpeta_db = "db_chats"
        self.carpeta_web = "Informacion_web"
        os.makedirs(self.carpeta_db, exist_ok=True)
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
        try:
            with console.status("[bold blue]Rastreando web...[/bold blue]"):
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "aside", "header"]): 
                    s.decompose()
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
        if os.path.exists(self.carpeta_web):
            for arch in os.listdir(self.carpeta_web):
                if arch.endswith(".md"):
                    with open(os.path.join(self.carpeta_web, arch), "r", encoding="utf-8") as f:
                        contexto_global += f"  <fuente archivo='{arch}'>\n{f.read()}\n</fuente>\n"
        contexto_global += "</MEMORIA_WEB_GLOBAL>\n"

        contexto_selectivo = "<DIARIOS_SELECCIONADOS>\n"
        for id_c in lista_ids:
            ruta = f"{self.carpeta_db}/chat_{id_c}.txt"
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    contexto_selectivo += f"  <diario id='{id_c}'>\n{f.read()}\n</diario>\n"
        contexto_selectivo += "</DIARIOS_SELECCIONADOS>"

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
            if ids:
                console.print(f"Memorias: {', '.join([f'[bold]{i+1}[/bold]:{n}' for i, n in enumerate(ids)])}")
                sel = Prompt.ask("Elige números (ej: 1,2) o '0' para ninguna")
                sel_ids = [ids[int(i)-1] for i in sel.split(",") if i != "0"]
            else:
                sel_ids = []
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
            if ids:
                for i, n in enumerate(ids): console.print(f"{i+1}. {n}")
                sel = IntPrompt.ask("Número")
                nexo.activar_modo_sueno(ids[sel-1])
        elif op == "5": break
