import os
import sys
import time
import json
import shutil
import zipfile
import threading
import subprocess
import re
import urllib.request
import math
from datetime import timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import requests
import asyncio
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

# Tenta importar Pyrogram no início para evitar travamento de Thread
try:
    from pyrogram import Client
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    print("AVISO: Pyrogram não instalado via pip install pyrogram tgcrypto")

try:
    import tgcrypto
    TGCRYPTO_AVAILABLE = True
except ImportError:
    TGCRYPTO_AVAILABLE = False

# ==================================================================================
# CONFIGURAÇÕES
# ==================================================================================

# Chaves de API
API_ID = 25946794
API_HASH = "c13ab5fe029cb271522873732cfac4e6"

DOODSTREAM_KEY = "556260hzehzrz5kh6crwvz"
STREAMTAPE_LOGIN = "6f4fcf8d0f2f9b1fefe0"   
STREAMTAPE_KEY = "vDQxaexXbOC4pml"
ABYSS_KEY = "18815a992014c504fc9ed85391b76e89"
FOLDER_NAME = "Filmes" # Pasta remota (Note a Maiúscula)

# FFmpeg
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_EXE = "ffmpeg.exe"
FFPROBE_EXE = "ffprobe.exe"

# ==================================================================================
# CLASSE PRINCIPAL DA INTERFACE (GUI)
# ==================================================================================

class VideoOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Otimizador de Vídeos - Antigravity")
        self.geometry("900x700")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Variáveis de Configuração Persistente
        self.config_file = "config.json"
        
        # Variáveis de Controle
        self.folder_path = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Rápido")
        self.remote_folder_var = tk.StringVar(value="Filmes")
        
        # Novas Opções
        self.turbo_var = ctk.BooleanVar(value=False)
        self.sites_var = ctk.BooleanVar(value=True) 
        self.telegram_var = ctk.BooleanVar(value=False)
        self.telegram_token = tk.StringVar()
        self.telegram_chat = tk.StringVar()

        self.is_running = False
        self.stop_event = threading.Event()

        # Carregar Configurações Salvas
        self.load_config()

        # Layout
        self.create_widgets()
        
        # Verificar dependências após carregar UI (segurança da UI)
        self.after(500, self.check_dependencies)

    def create_widgets(self):
        # 1. Título e Seleção de Pasta
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(pady=20, padx=20, fill="x")

        self.lbl_title = ctk.CTkLabel(self.frame_top, text="Otimizador & Uploader de Vídeos", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=10)

        self.btn_folder = ctk.CTkButton(self.frame_top, text="📂 Selecionar Pasta com Vídeos", command=self.select_folder)
        self.btn_folder.pack(pady=5)

        self.lbl_folder = ctk.CTkLabel(self.frame_top, textvariable=self.folder_path, text_color="gray")
        self.lbl_folder.pack(pady=5)

        # 2. Configurações
        self.frame_config = ctk.CTkFrame(self)
        self.frame_config.pack(pady=10, padx=20, fill="x")

        # Seleção de Pasta de Saída
        self.btn_output = ctk.CTkButton(self.frame_config, text="📂 Pasta de Saída (Opcional)", command=self.select_output_folder, fg_color="gray")
        self.btn_output.grid(row=0, column=0, padx=10, pady=5)
        self.lbl_output = ctk.CTkLabel(self.frame_config, text="Padrão: Subpasta 'Otimizados_Web'", text_color="gray", font=("Arial", 10))
        self.lbl_output.grid(row=1, column=0, padx=10, pady=0)

        # Nome da Pasta Remota (Upload)
        self.lbl_remote = ctk.CTkLabel(self.frame_config, text="Pasta no Site (Upload):")
        self.lbl_remote.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        self.entry_remote_folder = ctk.CTkEntry(self.frame_config, width=150)
        self.entry_remote_folder.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_remote_folder.insert(0, "Filmes")

        self.btn_scan = ctk.CTkButton(self.frame_config, text="🔍 Scan Pastas", command=self.open_scan_dialog, width=100, fg_color="purple")
        self.btn_scan.grid(row=0, column=3, padx=5, pady=5)

        self.lbl_mode = ctk.CTkLabel(self.frame_config, text="Modo de Otimização:")
        self.lbl_mode.grid(row=2, column=0, padx=10, pady=10)

        self.combo_mode = ctk.CTkComboBox(self.frame_config, values=[
            "Rápido (Copiar Vídeo, Converter Áudio)", 
            "Perfeito (CPU - Libx264 - Lento)",
            "Perfeito (GPU Intel - QuickSync - Rápido)",
            "Apenas Upload (Sem Converter)"
        ], variable=self.mode_var, width=300)
        self.combo_mode.grid(row=2, column=1, columnspan=2, padx=10, pady=10)

        # Opções Extras (Turbo e Telegram)
        self.frame_options = ctk.CTkFrame(self.frame_config, fg_color="transparent")
        self.frame_options.grid(row=3, column=0, columnspan=4, pady=10, sticky="ew")
        
        self.chk_turbo = ctk.CTkSwitch(self.frame_options, text="⚡ Modo Turbo", variable=self.turbo_var)
        self.chk_turbo.pack(side="left", padx=10)

        self.chk_sites = ctk.CTkSwitch(self.frame_options, text="🌐 Enviar Sites", variable=self.sites_var)
        self.chk_sites.pack(side="left", padx=10)

        self.chk_telegram = ctk.CTkSwitch(self.frame_options, text="✈️ Telegram", variable=self.telegram_var, command=self.toggle_telegram_fields)
        self.chk_telegram.pack(side="left", padx=10)

        # Campos Telegram (Inicialmente ocultos ou visíveis dependendo do estado)
        self.frame_telegram = ctk.CTkFrame(self.frame_config)
        
        self.entry_tg_token = ctk.CTkEntry(self.frame_telegram, textvariable=self.telegram_token, placeholder_text="Bot Token", width=200)
        self.entry_tg_token.pack(side="left", padx=5)
        
        self.entry_tg_chat = ctk.CTkEntry(self.frame_telegram, textvariable=self.telegram_chat, placeholder_text="Chat ID", width=100)
        self.entry_tg_chat.pack(side="left", padx=5)
        
        if self.telegram_var.get():
             self.frame_telegram.grid(row=4, column=0, columnspan=4, pady=5)

        self.btn_start = ctk.CTkButton(self.frame_config, text="🚀 INICIAR PROCESSAMENTO", command=self.buffer_start_process, fg_color="green", height=40)
        self.btn_start.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        # 3. Progresso
        self.frame_progress = ctk.CTkFrame(self)
        self.frame_progress.pack(pady=10, padx=20, fill="x")

        # Progresso Total
        self.lbl_total_progress = ctk.CTkLabel(self.frame_progress, text="Progresso Total (Arquivos):")
        self.lbl_total_progress.pack(anchor="w", padx=10, pady=(10,0))
        self.progress_bar_total = ctk.CTkProgressBar(self.frame_progress)
        self.progress_bar_total.pack(fill="x", padx=10, pady=5)
        self.progress_bar_total.set(0)

        # Progresso Atual (Tarefa)
        self.lbl_current_task = ctk.CTkLabel(self.frame_progress, text="Tarefa Atual: Aguardando...", font=("Roboto", 14))
        self.lbl_current_task.pack(anchor="w", padx=10, pady=(10,0))
        
        self.progress_bar_current = ctk.CTkProgressBar(self.frame_progress,  progress_color="orange")
        self.progress_bar_current.pack(fill="x", padx=10, pady=5)
        self.progress_bar_current.set(0)

        self.lbl_eta = ctk.CTkLabel(self.frame_progress, text="Estimativa: --:--:--", text_color="yellow")
        self.lbl_eta.pack(pady=5)

        # 4. Logs
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.pack(pady=10, padx=20, fill="both", expand=True)

        self.lbl_log = ctk.CTkLabel(self.frame_log, text="Log de Execução:")
        self.lbl_log.pack(anchor="w", padx=10, pady=5)

        self.txt_log = ctk.CTkTextbox(self.frame_log, height=200)
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------
    # FUNÇÕES DE UI E LOG
    # ------------------------------------------------------------------
    
    def log(self, message):
        """Escreve no log da interface de forma segura para threads."""
        self.after(0, lambda: self._log_internal(message))

    def _log_internal(self, message):
        try:
             if hasattr(self, 'txt_log') and self.txt_log:
                self.txt_log.insert("end", message + "\n")
                self.txt_log.see("end")
             else:
                print(f"[LOG]: {message}")
        except Exception as e:
             print(f"[LOG ERROR]: {message} | {e}")

    def update_status(self, task_name, progress=0.0, eta_text=""):
        """Atualiza barra de progresso e texto da tarefa atual."""
        self.after(0, lambda: self._update_status_internal(task_name, progress, eta_text))

    def _update_status_internal(self, task_name, progress, eta_text):
        self.lbl_current_task.configure(text=f"Tarefa Atual: {task_name}")
        self.progress_bar_current.set(progress)
        if eta_text:
            self.lbl_eta.configure(text=f"Estimativa: {eta_text}")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.log(f"📂 Pasta selecionada: {folder}")

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path_var.set(folder)
            self.lbl_output.configure(text=f"Saída: {folder}", text_color="white")
            self.log(f"📂 Pasta de Saída definida: {folder}")

    def toggle_telegram_fields(self):
        if self.telegram_var.get():
            self.frame_telegram.grid(row=4, column=0, columnspan=4, pady=5)
        else:
            self.frame_telegram.grid_forget()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.folder_path.set(data.get('folder_path', ''))
                    self.output_path_var.set(data.get('output_path', ''))
                    self.remote_folder_var.set(data.get('remote_folder', 'Filmes'))
                    self.remote_folder_var.set(data.get('remote_folder', 'Filmes'))
                    self.remote_folder_var.set(data.get('remote_folder', 'Filmes'))
                    self.turbo_var.set(data.get('turbo_mode', False))
                    self.sites_var.set(data.get('sites_enabled', True))
                    self.telegram_var.set(data.get('telegram_enabled', False))
                    self.telegram_token.set(data.get('telegram_token', ''))
                    self.telegram_chat.set(data.get('telegram_chat', ''))
        except: pass

    def save_config(self):
        data = {
            'folder_path': self.folder_path.get(),
            'output_path': self.output_path_var.get(),
            'remote_folder': self.entry_remote_folder.get(),
            'turbo_mode': self.turbo_var.get(),
            'sites_enabled': self.sites_var.get(),
            'telegram_enabled': self.telegram_var.get(),
            'telegram_token': self.telegram_token.get(),
            'telegram_chat': self.telegram_chat.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f)
        except: pass

    def open_scan_dialog(self):
        self.log("🔍 Iniciando Scan de pastas remotas...")
        threading.Thread(target=self.fetch_folders_thread, daemon=True).start()

    def fetch_folders_thread(self):
        # DoodStream
        dood_folders = []
        try:
            r = requests.get(f"https://doodapi.com/api/folder/list?key={DOODSTREAM_KEY}").json()
            if r['msg'] == 'OK':
                dood_folders = [f['name'] for f in r['result']['folders']]
        except: pass

        # Abyss
        abyss_folders = []
        try:
            r = requests.get(f"https://api.abyss.to/v1/folders/list?key={ABYSS_KEY}&maxResults=100").json()
            if 'items' in r:
                abyss_folders = [f['name'] for f in r['items']]
        except: pass

        # StreamTape (Listagem limitada, tenta pegar da raiz)
        st_folders = []
        try:
            r = requests.get(f"https://api.streamtape.com/file/listfolder?login={STREAMTAPE_LOGIN}&key={STREAMTAPE_KEY}").json()
            if r['status'] == 200:
                folders = r.get('result', {}).get('folders', [])
                if isinstance(folders, list):
                   st_folders = [f['name'] for f in folders]
        except: pass

        # Consolidar nomes únicos
        all_folders = sorted(list(set(dood_folders + abyss_folders + st_folders)))
        self.after(0, lambda: self.show_folder_selection(all_folders))

    def show_folder_selection(self, folders):
        if not folders:
            self.log("⚠️ Nenhuma pasta encontrada nos sites.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Selecionar Pasta Remota")
        dialog.geometry("400x400")
        
        lbl = ctk.CTkLabel(dialog, text="Pastas Encontradas (Clique para usar):", font=("Roboto", 14, "bold"))
        lbl.pack(pady=10)

        scroll = ctk.CTkScrollableFrame(dialog, width=350, height=300)
        scroll.pack(pady=5, padx=10)

        def select(name):
            self.entry_remote_folder.delete(0, tk.END)
            self.entry_remote_folder.insert(0, name)
            self.log(f"✅ Pasta '{name}' selecionada para upload.")
            dialog.destroy()

        for f in folders:
            btn = ctk.CTkButton(scroll, text=f, command=lambda n=f: select(n), fg_color="darkblue")
            btn.pack(pady=2, fill="x")

    def check_dependencies(self):
        if not os.path.exists(FFMPEG_EXE) or not os.path.exists(FFPROBE_EXE):
            self.log("⚠️ FFmpeg não encontrado. Baixando automaticamente... (Aguarde para Iniciar)")
            self.btn_start.configure(state="disabled", text="Baixando Dependências...")
            threading.Thread(target=self.download_ffmpeg_thread).start()
        else:
            self.log("✅ FFmpeg encontrado.")

    def download_ffmpeg_thread(self):
        try:
            urllib.request.urlretrieve(FFMPEG_URL, "ffmpeg.zip")
            with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("bin/ffmpeg.exe"):
                        with zip_ref.open(file) as source, open(FFMPEG_EXE, "wb") as target:
                            shutil.copyfileobj(source, target)
                    elif file.endswith("bin/ffprobe.exe"):
                        with zip_ref.open(file) as source, open(FFPROBE_EXE, "wb") as target:
                            shutil.copyfileobj(source, target)
            os.remove("ffmpeg.zip")
            self.log("✅ FFmpeg baixado e instalado com sucesso!")
            # Reabilitar botão na UI principal
            self.after(0, lambda: self.btn_start.configure(state="normal", text="🚀 INICIAR PROCESSAMENTO"))
        except Exception as e:
            self.log(f"❌ Erro ao baixar FFmpeg: {e}")
            self.after(0, lambda: self.btn_start.configure(text="Erro no Download (Baixe Manualmente)"))

    # ------------------------------------------------------------------
    # LÓGICA PRINCIPAL (THREAD)
    # ------------------------------------------------------------------

    def buffer_start_process(self):
        print("DEBUG: Botão Iniciar Clicado") # Console
        self.log("🖱️ Botão Iniciar Pressionado...")
        if self.is_running:
            self.log("Solicitando parada... Aguarde finalizar tarefa atual.")
            self.stop_event.set()
        else:
            self.start_thread()

    def start_thread(self):
        folder = self.folder_path.get()
        print(f"DEBUG: Pasta selecionada: {folder}")
        
        if not folder:
            self.log("❌ Selecione uma pasta primeiro!")
            return

        if self.telegram_var.get():
            token = self.telegram_token.get()
            chat = self.telegram_chat.get()
            
            if not token or not chat:
                self.log("❌ Erro: Para enviar ao Telegram, preencha o Token e o Chat ID!")
                return

        self.is_running = True
        self.btn_start.configure(text="🛑 PARAR (Aguarde o fim da tarefa atual)", fg_color="red")
        self.stop_event.clear()
        
        self.log("🚀 Iniciando Thread de Processamento...")
        
        # Leitura SEGURA de todas as variáveis na Main Thread
        config = {
            'folder': folder,
            'remote_folder_name': self.entry_remote_folder.get().strip() or "Filmes",
            'output_folder_custom': self.output_path_var.get(),
            'mode': self.mode_var.get(),
            'turbo': self.turbo_var.get(),
            'sites_enabled': self.sites_var.get(),
            'telegram_enabled': self.telegram_var.get(),
            'telegram_token': self.telegram_token.get(),
            'telegram_chat': self.telegram_chat.get()
        }
        self.save_config()

        # Inicia a thread pesada passando o dicionário de configuração
        threading.Thread(target=self.run_process, args=(config,), daemon=True).start()


    def run_process(self, config):
        print("DEBUG: Thread run_process iniciou (Config OK).")
        try:
            folder = config['folder']
            remote_folder_name = config['remote_folder_name']
            
            # Atualiza a global apenas para referência
            global FOLDER_NAME 
            FOLDER_NAME = remote_folder_name

            reencode_mode = "Perfeito" in config['mode']
            
            extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov']
            files = []
            print(f"DEBUG: Procurando vídeos em: {folder}")
            for ext in extensions:
                found = list(Path(folder).glob(ext))
                print(f"DEBUG: Buscando {ext} -> Encontrados: {len(found)}")
                files.extend(found)
            
            print(f"DEBUG: Total arquivos encontrados: {len(files)}")
            
            total_files = len(files)
            if total_files == 0:
                self.log("⚠️ Nenhum vídeo encontrado.")
                self.finish_process()
                return

            print("DEBUG: Checkpoint 1 - Iniciando Logs")
            self.log(f"🚀 Iniciando processamento de {total_files} vídeos...")
            self.log(f"☁️ Pasta Remota (Upload): {FOLDER_NAME}")
            print("DEBUG: Checkpoint 2 - Logs Feitos")
            
            # Define pasta de saída
            if config['output_folder_custom']:
                # Se o usuário escolheu uma pasta, USA ELA DIRETO (sem subpasta)
                output_folder = config['output_folder_custom']
            else:
                # Se não escolheu, cria a subpasta padrão na origem
                output_folder = os.path.join(folder, "Otimizados_Web")
            
            print(f"DEBUG: Checkpoint 3 - Criando pasta {output_folder}")
            os.makedirs(output_folder, exist_ok=True)
            print("DEBUG: Checkpoint 4 - Pasta OK")

            for i, video in enumerate(files):
                print(f"DEBUG: Loop Arquivo {i+1}: {video.name}")
                if self.stop_event.is_set():
                    self.log("🛑 Processo interrompido pelo usuário.")
                    break

                # Atualiza progresso total
                total_prog = i / total_files
                self.after(0, lambda: self.progress_bar_total.set(total_prog))
                
                video_path = str(video)
                dest_name = video.stem + ".mp4"
                output_path = os.path.join(output_folder, dest_name)
                
                print(f"DEBUG: Processando {video.name}")
                print(f"DEBUG: Modo selecionado: '{config['mode']}'")

                self.log(f"\n🎬 [{i+1}/{total_files}] Processando: {video.name}")

                # 1. CONVERSÃO
                success = True
                if "Apenas Upload" in config['mode']:
                     self.log("   ⏩ Pulando conversão (Modo Apenas Upload).")
                     if not os.path.exists(output_path) and os.path.exists(video_path):
                         # output vira source original
                         output_path = video_path 
                else:
                    if os.path.exists(output_path):
                        self.log("   ⚠️ Arquivo otimizado já existe. Pulando conversão.")
                    else:
                        success = self.convert_video(video_path, output_path, reencode_mode)
                    
                    if not success:
                        self.log("   ❌ Falha na conversão ou cancelado. Pulando uploads.")
                        continue

                if self.stop_event.is_set(): break

                # 2. UPLOADS
                upload_funcs = []
                
                print(f"DEBUG: Config Telegram Enabled: {config['telegram_enabled']}")

                if config['sites_enabled']:
                    upload_funcs.extend([self.upload_doodstream, self.upload_streamtape, self.upload_abyss])
                
                if config['telegram_enabled']:
                     print("DEBUG: Adicionando funcao de upload Telegram")
                     # Usa lambda para passar os tokens seguros
                     upload_funcs.append(lambda p: self.upload_telegram(p, config['telegram_token'], config['telegram_chat']))

                if not upload_funcs:
                    self.log("   ⚠️ Nenhuma opção de upload selecionada.")
                    continue

                if config['turbo']:
                    self.log("   ⚡ Modo Turbo: Iniciando uploads simultâneos...")
                    threads = []
                    for func in upload_funcs:
                        t = threading.Thread(target=func, args=(output_path,))
                        t.start()
                        threads.append(t)
                    
                    # Aguardar todos terminarem
                    for t in threads:
                        t.join()
                else:
                    # Sequencial
                    for func in upload_funcs:
                         if self.stop_event.is_set(): break
                         if self.stop_event.is_set(): break
                         print(f"DEBUG: Executando upload index {upload_funcs.index(func)}")
                         try:
                             func(output_path)
                             print(f"DEBUG: Upload index {upload_funcs.index(func)} CONCLUIDO")
                         except Exception as e_up:
                             print(f"DEBUG: Erro ao executar upload: {e_up}")
                             self.log(f"❌ Erro ao chamar função de upload: {e_up}")
                
                self.log(f"   ✅ Arquivo {video.name} finalizado!")

            self.finish_process()
        except Exception as e:
            self.log(f"❌ Erro Crítico: {e}")
            self.finish_process()

    def finish_process(self):
        self.is_running = False
        self.stop_event.clear()
        self.after(0, lambda: self.btn_start.configure(state="normal", text="🚀 INICIAR PROCESSAMENTO", fg_color="green"))
        self.after(0, lambda: self.progress_bar_total.set(1.0))
        self.update_status("Concluído!", 1.0, "---")
        self.log("\n🎉 Processo finalizado!")

    # ------------------------------------------------------------------
    # FUNÇÕES DE CONVERSÃO E UPLOAD
    # ------------------------------------------------------------------

    def get_duration(self, file_path):
        """Pega duração em segundos usando ffprobe."""
        try:
            cmd = [FFPROBE_EXE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0.0

    def convert_video(self, input_path, output_path, reencode=False):
        """Converte vídeo com barra de progresso."""
        self.update_status("Convertendo (FFmpeg)...", 0, "Calculando...")
        
        duration = self.get_duration(input_path)
        if duration == 0:
            self.log("   ⚠️ Não foi possível ler duração. Progresso será estimado.")
            duration = 1 # Evitar div por zero

        # Comando
        cmd = [FFMPEG_EXE, '-y', '-i', input_path]
        
        # Mapeamento
        cmd.extend(['-map', '0:v:0', '-map', '0:a:0'])

        mode = self.mode_var.get()

        if "Rápido (Copiar" in mode:
            # Modo Copy
            cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-ac', '2'])
        
        elif "GPU Intel" in mode:
            # Modo Intel QuickSync (Hardware)
            # Requer h264_qsv. 
            # Ajustes: global_quality (ICQ) ou bitrate fixo. Vamos usar bitrate max para web.
            cmd.extend([
                '-c:v', 'h264_qsv', 
                '-preset', 'veryfast', 
                '-global_quality', '24', # Similar a CRF
                '-maxrate', '2500k', 
                '-bufsize', '5000k',
                '-c:a', 'aac', '-b:a', '128k', '-ac', '2'
            ])
            
        else:
            # Modo CPU (Original Perfeito)
            cmd.extend([
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '24', 
                '-maxrate', '2500k', '-bufsize', '5000k',
                '-c:a', 'aac', '-b:a', '128k', '-ac', '2'
            ])
        
        cmd.extend(['-movflags', '+faststart', output_path])

        # Execução com leitura de progresso
        creation_flags = 0
        # Execução com leitura de progresso
        creation_flags = 0
        if sys.platform == 'win32':
             creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, creationflags=creation_flags)
        
        start_time = time.time()
        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})')

        stderr_stream = process.stderr
        if stderr_stream is None:
            self.log("❌ Erro interno: Não foi possível capturar a saída do processo de conversão.")
            return False

        for line in stderr_stream:
                if self.stop_event.is_set():
                    process.terminate()
                    return False
                
                match = time_pattern.search(line)
                if match:
                    h, m, s = map(float, match.groups())
                    current_acc = h*3600 + m*60 + s
                    progress = min(current_acc / duration, 1.0)
                    
                    elapsed = time.time() - start_time
                    if progress > 0.01:
                        eta_seconds = (elapsed / progress) - elapsed
                        eta_str = str(timedelta(seconds=int(eta_seconds)))
                        # Throttle update
                        if int(elapsed * 10) % 2 == 0:
                            self.update_status(f"Convertendo... ({int(progress*100)}%)", progress, eta_str)

        process.wait()
        return process.returncode == 0

    def upload_file_generic(self, file_path, url, fields, service_name):
        """Upload genérico com monitoramento de progresso usando requests-toolbelt."""
        self.update_status(f"Enviando para {service_name}...", 0, "Iniciando...")
        
        file_size = os.path.getsize(file_path)
        start_time = time.time()

        def callback(monitor):
            if self.stop_event.is_set():
                # Não dá pra cancelar request via callback facilmente, mas podemos avisar UI
                return
            
            bytes_read = monitor.bytes_read
            progress = bytes_read / file_size
            
            elapsed = time.time() - start_time
            if elapsed > 0 and progress > 0.01:
                speed = bytes_read / elapsed # bytes por seg
                remaining_bytes = file_size - bytes_read
                eta_seconds = remaining_bytes / speed
                eta_str = str(timedelta(seconds=int(eta_seconds)))
                
                if int(elapsed * 10) % 5 == 0: # Atualiza a cada ~0.5s
                    self.update_status(f"Enviando {service_name} ({int(progress*100)}%)", progress, eta_str)

        try:
            m = MultipartEncoder(fields=fields)
            monitor = MultipartEncoderMonitor(m, callback)
            headers = {'Content-Type': monitor.content_type}
            
            response = requests.post(url, data=monitor, headers=headers)
            return response.json()
        except Exception as e:
            self.log(f"   ❌ Erro Upload {service_name}: {e}")
            return None

    # ------------------------------------------------------------------
    # DoodStream
    # ------------------------------------------------------------------
    def get_dood_folder(self):
        url = f"https://doodapi.com/api/folder/list?key={DOODSTREAM_KEY}"
        try:
            resp = requests.get(url).json()
            if resp['msg'] == 'OK':
                for f in resp['result']['folders']:
                    if f['name'] == FOLDER_NAME:
                        return f['fld_id'] # Use fld_id
                # Criar
                c_url = f"https://doodapi.com/api/folder/create?key={DOODSTREAM_KEY}&name={FOLDER_NAME}"
                c_resp = requests.get(c_url).json()
                if c_resp['msg'] == 'OK':
                    return c_resp['result']['fld_id']
        except Exception as e:
            self.log(f"      ⚠️ Erro Pasta Dood: {e}")
            return None

    def upload_doodstream(self, file_path):
        self.log("   📤 Iniciando DoodStream...")
        try:
            folder_id = self.get_dood_folder()
            server = requests.get(f"https://doodapi.com/api/upload/server?key={DOODSTREAM_KEY}").json()
            if server['msg'] != 'OK':
                self.log("      ❌ Erro Servidor DoodStream")
                return

            upload_url = server['result']
            
            filename = os.path.basename(file_path)
            fields = {
                'api_key': DOODSTREAM_KEY,
                'file': (filename, open(file_path, 'rb'), 'video/mp4')
            }
            if folder_id:
                fields['fld_id'] = folder_id

            resp = self.upload_file_generic(file_path, upload_url, fields, "DoodStream")
            
            if resp and resp.get('msg') == 'OK':
                self.log(f"      ✅ Sucesso DoodStream: {resp['result']['download_url']}")
            else:
                self.log(f"      ❌ Falha DoodStream: {resp}")

        except Exception as e:
            self.log(f"      ❌ Erro DoodStream: {e}")

    # ------------------------------------------------------------------
    # StreamTape
    # ------------------------------------------------------------------
    def get_streamtape_folder(self):
        """Tenta encontrar o ID da pasta. StreamTape API pode variar."""
        url = f"https://api.streamtape.com/file/listfolder?login={STREAMTAPE_LOGIN}&key={STREAMTAPE_KEY}"
        try:
            resp = requests.get(url).json()
            if resp['status'] == 200:
                # Tenta estrutura result -> folders
                folders = resp.get('result', {}).get('folders', [])
                if not folders and isinstance(resp.get('result'), list):
                    # Tenta result lista direta (algumas apis antigas)
                    folders = resp['result']
                
                if isinstance(folders, list):
                    for f in folders:
                        if f.get('name') == FOLDER_NAME:
                            return f.get('id')
            else:
                 self.log(f"      ⚠️ StreamTape ListFolder: {resp.get('msg')}")
        except Exception as e:
            self.log(f"      ⚠️ Erro ao listar pastas StreamTape: {e}")
        
        self.log(f"      ⚠️ Pasta '{FOLDER_NAME}' não encontrada no StreamTape (Envio p/ Raiz).")
        return None

    def upload_streamtape(self, file_path):
        self.log("   📤 Iniciando StreamTape...")
        try:
            folder_id = self.get_streamtape_folder()
            
            # Pegar URL
            ul_url = f"https://api.streamtape.com/file/ul?login={STREAMTAPE_LOGIN}&key={STREAMTAPE_KEY}"
            if folder_id:
                ul_url += f"&folder={folder_id}"
            
            server_resp = requests.get(ul_url).json()
            if server_resp['status'] != 200:
                self.log(f"      ❌ Erro Servidor StreamTape: {server_resp.get('msg')}")
                return

            upload_target = server_resp['result']['url']
            
            filename = os.path.basename(file_path)
            fields = {
                'file': (filename, open(file_path, 'rb'), 'video/mp4')
            }
            
            resp = self.upload_file_generic(file_path, upload_target, fields, "StreamTape")
            
            if resp and resp.get('status') == 200:
                self.log(f"      ✅ Sucesso StreamTape: {resp['result']['url']}")
            else:
                self.log(f"      ❌ Falha StreamTape: {resp}")

        except Exception as e:
            self.log(f"      ❌ Erro StreamTape: {e}")

    # ------------------------------------------------------------------
    # Abyss.to
    # ------------------------------------------------------------------
    def get_abyss_folder(self):
        """Busca ou cria pasta no Abyss usando a API Key."""
        base_url = "https://api.abyss.to/v1"
        try:
            # Lista
            list_url = f"{base_url}/folders/list?key={ABYSS_KEY}&maxResults=100"
            resp = requests.get(list_url).json()
            
            if 'items' in resp:
                for f in resp['items']:
                    if f['name'] == FOLDER_NAME:
                        return f['id']
            
            # Criar
            create_url = f"{base_url}/folders?key={ABYSS_KEY}"
            # Nota: Documentação indica POST /folders com key como param ou header.
            payload = {"name": FOLDER_NAME}
            create_resp = requests.post(create_url, json=payload).json()
            
            if 'id' in create_resp:
                return create_resp['id']

        except Exception as e:
            self.log(f"      ⚠️ Erro ao buscar pasta Abyss: {e}")
        return None

    def upload_abyss(self, file_path):
        self.log("   📤 Iniciando Abyss.to...")
        try:
            # 1. Upload Direto
            url = f"http://up.abyss.to/{ABYSS_KEY}"
            
            fields = {
                'file': (os.path.basename(file_path), open(file_path, 'rb'), 'video/mp4')
            }
            
            resp = self.upload_file_generic(file_path, url, fields, "Abyss.to")
            
            if resp and 'slug' in resp:
                file_id = resp['slug']
                self.log(f"      ✅ Sucesso Abyss: ID {file_id}")
                
                # 2. Mover para Pasta
                folder_id = self.get_abyss_folder()
                if folder_id:
                    # Correção: Enviar parentId no corpo JSON
                    move_url = f"https://api.abyss.to/v1/files/{file_id}?key={ABYSS_KEY}"
                    resp_move = requests.patch(move_url, json={'parentId': folder_id})
                    
                    if resp_move.status_code == 200:
                        self.log(f"      📂 Movido para pasta '{FOLDER_NAME}'")
                    else:
                         self.log(f"      ⚠️ Erro ao mover Abyss: {resp_move.text}")
            else:
                self.log(f"      ❌ Falha Abyss: {resp}")

        except Exception as e:
            self.log(f"      ❌ Erro Abyss: {e}")

    
    
    def upload_telegram(self, file_path, token, chat_id):
        # Correção ID
        if len(str(chat_id)) >= 12 and not str(chat_id).startswith("-"):
            chat_id = int(f"-{chat_id}")
        else:
            try: chat_id = int(chat_id)
            except: pass

        self.log(f"   📤 Iniciando Telegram (MTProto 2GB)...")

        if not PYROGRAM_AVAILABLE:
            self.log("❌ ERRO: Biblioteca 'pyrogram' não instalada!")
            return

        # Execução Async Manual - Cria e fecha loop a cada arquivo para evitar conflitos em Threads
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._upload_telegram_async(file_path, token, chat_id))
            loop.close()
        except RuntimeError as re:
                self.log(f"      ❌ Erro Loop Async: {re} (Tente reiniciar o app)")
        except Exception as e:
                self.log(f"      ❌ Erro Crítico Telegram: {e}")

    async def _upload_telegram_async(self, file_path, token, chat_id):
        app = None
        try:
            session_name = os.path.join(os.getcwd(), "my_bot_session")
            # Iniciar Client SEMPRE dentro do loop async e usando Client diretamente
            # Otimização: workdir separado e ipv6 desativado por precaução
            # Aumentando para 8 workers para tentar uso max de banda
            workers_count = 8 if TGCRYPTO_AVAILABLE else 4 
            # ipv6=False é CRUCIAL para evitar lentidao em algumas rotas
            app = Client(session_name, api_id=API_ID, api_hash=API_HASH, bot_token=token, workers=workers_count, max_concurrent_transmissions=workers_count, ipv6=False)

            await app.start()
            tg_status = "✅ ULTRA RÁPIDO (TgCrypto Ativo)" if TGCRYPTO_AVAILABLE else "⚠️ LENTO (Sem aceleração C++)"
            self.log(f"      🔌 Conectado ao Telegram! Status: {tg_status}")
            self.log(f"      ℹ️ Usando {workers_count} conexões simultâneas (IPv4 Forçado)")

            # Armazena estado para calular velocidade
            self.last_update_time = time.time()
            self.last_uploaded = 0
            
            def prog_func(current, total):
                try:
                    if total > 0:
                        now = time.time()
                        # Atualiza a cada 1.5 segundos para não travar a UI
                        if now - self.last_update_time > 1.5:
                            progress = current / total
                            
                            # Calcula velocidade
                            delta_bytes = current - self.last_uploaded
                            delta_time = now - self.last_update_time
                            speed = delta_bytes / delta_time if delta_time > 0 else 0
                            speed_str = f"{speed/1024/1024:.2f} MB/s"
                            
                            eta_seconds = (total - current) / speed if speed > 0 else 0
                            eta_str = str(timedelta(seconds=int(eta_seconds)))

                            self.update_status(f"Telegram: {int(progress*100)}% ({speed_str})", progress, eta_str)
                            
                            self.last_update_time = now
                            self.last_uploaded = current
                except Exception as e:
                    print(f"DEBUG: Erro no callback de progresso: {e}")

            video_msg = await app.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=f"🎬 {os.path.basename(file_path)}",
                progress=prog_func
            )
            
            # Verificacao de Tamanho
            original_size = os.path.getsize(file_path)
            sent_size = getattr(video_msg.video, 'file_size', 0) if video_msg and video_msg.video else 0
            
            if video_msg:
                if sent_size > 0 and abs(sent_size - original_size) > 1024*1024: # Diferenca > 1MB
                     self.log(f"      ⚠️ ALERTA: Tamanho diferente! Enviado: {sent_size/1024/1024:.1f}MB, Original: {original_size/1024/1024:.1f}MB")
                self.log(f"      ✅ Sucesso Telegram! (Msg ID: {video_msg.id})")
            else:
                self.log("      ❌ Falha envio Telegram (Sem retorno).")

        except Exception as e:
            err_msg = str(e)
            if "PEER_ID_INVALID" in err_msg.upper() or "Peer id invalid" in err_msg:
                self.log(f"      ❌ Erro ID: O Bot não encontrou esse Chat ID ({chat_id}).")
                self.log("      👉 Dica: Se for CANAL, o Bot precisa ser ADMIN lá.")
                self.log("      👉 Dica: Se for PESSOAL, verifique seu ID no @userinfobot.")
            else:
                self.log(f"      ❌ Erro Async: {err_msg}")
        finally:
            if app:
                try:
                    if app.is_connected:
                        await app.stop()
                except: pass
            
            # Pequena pausa para garantir que tarefas background morram
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        app = VideoOptimizerApp()
        app.mainloop()
    except Exception as e:
        print(f"❌ Erro Fatal: {e}")
        import traceback
        traceback.print_exc()
        input("Pressione Enter para sair...")
