import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import glob
import threading
import shutil # Para copiar arquivos de fonte
from tkinter import filedialog, colorchooser
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# --- CONFIGURAÇÕES GLOBAIS ---
PASTA_TEMAS = "temas_imagens"
PASTA_FONTES = "minhas_fontes"
LARGURA_BASE = 800
ALTURA_BASE = 400

# Garante que as pastas existem
for p in [PASTA_TEMAS, PASTA_FONTES]:
    if not os.path.exists(p): os.makedirs(p)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppEtiquetasV4(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gerador de Etiquetas Escolar - BY ADRIANO FERREIRA")
        self.geometry("1300x850")
        
        # --- ESTADO E VARIÁVEIS ---
        self.img_original = None
        
        # Variáveis de Imagem (Background)
        self.bg_zoom = 1.0
        self.bg_offset_x = 0
        self.bg_offset_y = 0
        
        # Variáveis de Texto (Dicionário de Configuração)
        # Aqui guardamos a posição e tamanho de CADA elemento separadamente
        self.config_textos = {
            "ALUNO":   {"x": 0, "y": -120, "size": 60, "color": "#FFFFFF", "font": "arialbd.ttf", "text": ""},
            "MATÉRIA": {"x": 0, "y": 0,    "size": 90, "color": "#FFFFFF", "font": "arialbd.ttf", "text": "MATÉRIA"},
            "TURMA":   {"x": 0, "y": 120,  "size": 50, "color": "#FFFFFF", "font": "arial.ttf",   "text": ""}
        }
        
        self.elemento_selecionado = "ALUNO" # Qual texto estamos editando agora?
        self.cor_sombra = "#000000"
        
        # UX (Arrastar Imagem)
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # OTIMIZAÇÃO
        self.job_render = None 

        self.setup_ui()
        self.carregar_catalogo()
        self.atualizar_lista_fontes()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === BARRA LATERAL ===
        self.sidebar = ctk.CTkFrame(self, width=350, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="EDITOR STUDIO V4", font=("Roboto", 24, "bold")).pack(pady=20)

        # Abas
        self.tabview = ctk.CTkTabview(self.sidebar)
        self.tabview.pack(padx=10, fill="both", expand=True)
        
        self.tab_dados = self.tabview.add("Dados")
        self.tab_texto = self.tabview.add("Edição Texto") # NOVA ABA
        self.tab_galeria = self.tabview.add("Galeria")

        # --- ABA 1: DADOS ---
        self.entry_nome = ctk.CTkEntry(self.tab_dados, placeholder_text="Nome do Aluno")
        self.entry_nome.pack(fill="x", pady=10)
        self.entry_nome.bind("<KeyRelease>", self.atualizar_texto_inputs)

        self.entry_turma = ctk.CTkEntry(self.tab_dados, placeholder_text="Turma / Série")
        self.entry_turma.pack(fill="x", pady=10)
        self.entry_turma.bind("<KeyRelease>", self.atualizar_texto_inputs)

        ctk.CTkLabel(self.tab_dados, text="Lista de Matérias:").pack(pady=(20,0))
        self.txt_materias = ctk.CTkTextbox(self.tab_dados, height=200)
        self.txt_materias.insert("0.0", "PORTUGUÊS\nMATEMÁTICA\nHISTÓRIA\nGEOGRAFIA\nCIÊNCIAS\nINGLÊS\nARTES")
        self.txt_materias.pack(fill="x", pady=5)

        # --- ABA 2: EDIÇÃO DE TEXTO (NOVIDADE) ---
        ctk.CTkLabel(self.tab_texto, text="Selecione o elemento para editar:", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Seletor de qual texto editar
        self.combo_elemento = ctk.CTkSegmentedButton(self.tab_texto, values=["ALUNO", "MATÉRIA", "TURMA"], command=self.mudar_elemento_foco)
        self.combo_elemento.set("ALUNO")
        self.combo_elemento.pack(fill="x", pady=5)

        # Frame de Controles
        self.frame_controles_texto = ctk.CTkFrame(self.tab_texto, fg_color="transparent")
        self.frame_controles_texto.pack(fill="both", expand=True, pady=10)

        # Sliders de Posição
        ctk.CTkLabel(self.frame_controles_texto, text="Posição Vertical (Y)").pack()
        self.slider_text_y = ctk.CTkSlider(self.frame_controles_texto, from_=-300, to=300, command=self.atualizar_params_texto)
        self.slider_text_y.pack(fill="x", pady=5)
        
        ctk.CTkLabel(self.frame_controles_texto, text="Posição Horizontal (X)").pack()
        self.slider_text_x = ctk.CTkSlider(self.frame_controles_texto, from_=-400, to=400, command=self.atualizar_params_texto)
        self.slider_text_x.pack(fill="x", pady=5)

        # Tamanho da Fonte
        ctk.CTkLabel(self.frame_controles_texto, text="Tamanho da Fonte").pack(pady=(15,0))
        self.slider_font_size = ctk.CTkSlider(self.frame_controles_texto, from_=10, to=200, command=self.atualizar_params_texto)
        self.slider_font_size.pack(fill="x", pady=5)

        # Fontes e Cores
        ctk.CTkLabel(self.frame_controles_texto, text="Estilo").pack(pady=(15,0))
        self.combo_fontes = ctk.CTkComboBox(self.frame_controles_texto, values=[], command=self.mudar_fonte_atual)
        self.combo_fontes.pack(fill="x", pady=5)
        
        self.btn_importar_fonte = ctk.CTkButton(self.frame_controles_texto, text="📥 Importar Nova Fonte", fg_color="#555", command=self.importar_fonte)
        self.btn_importar_fonte.pack(fill="x", pady=5)

        self.btn_cor_texto = ctk.CTkButton(self.frame_controles_texto, text="🎨 Cor deste Texto", command=self.escolher_cor_texto)
        self.btn_cor_texto.pack(fill="x", pady=10)
        
        self.btn_reset = ctk.CTkButton(self.frame_controles_texto, text="↺ Resetar Posição", fg_color="gray", command=self.resetar_posicao)
        self.btn_reset.pack(fill="x", pady=5)

        # --- ABA 3: GALERIA ---
        self.btn_upload = ctk.CTkButton(self.tab_galeria, text="📂 Carregar Fundo", command=self.upload_imagem, fg_color="#E67E22")
        self.btn_upload.pack(fill="x", pady=10)
        self.scroll_imgs = ctk.CTkScrollableFrame(self.tab_galeria, label_text="Meus Temas")
        self.scroll_imgs.pack(fill="both", expand=True)

        # === ÁREA PRINCIPAL ===
        self.main_area = ctk.CTkFrame(self)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Canvas Preview
        self.canvas_preview = ctk.CTkCanvas(self.main_area, bg="#202020", highlightthickness=0)
        self.canvas_preview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Eventos do Canvas (Zoom e Drag da Imagem de Fundo)
        self.canvas_preview.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas_preview.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas_preview.bind("<MouseWheel>", self.on_zoom)

        # Botão Gerar
        self.btn_gerar = ctk.CTkButton(self.main_area, text="GERAR PDF FINAL", height=60, fg_color="#27AE60", font=("Arial", 18, "bold"), command=self.iniciar_geracao_pdf)
        self.btn_gerar.pack(fill="x", pady=10)
        
        self.barra_progresso = ctk.CTkProgressBar(self.main_area)
        self.barra_progresso.pack(fill="x", pady=(0, 10))
        self.barra_progresso.pack_forget()

        # Inicializa valores dos sliders
        self.atualizar_controles_ui()

    # --- LÓGICA DE TEXTO V4 ---

    def atualizar_texto_inputs(self, event=None):
        """Atualiza o dicionário quando o usuário digita nos campos Nome/Turma"""
        self.config_textos["ALUNO"]["text"] = self.entry_nome.get()
        self.config_textos["TURMA"]["text"] = self.entry_turma.get()
        self.agendar_render()

    def mudar_elemento_foco(self, valor):
        """Quando o usuário troca a aba (Aluno -> Turma), atualiza os sliders para mostrar os valores daquele item"""
        self.elemento_selecionado = valor
        self.atualizar_controles_ui()

    def atualizar_controles_ui(self):
        """Pega os dados do dicionário e joga nos sliders"""
        dados = self.config_textos[self.elemento_selecionado]
        self.slider_text_x.set(dados["x"])
        self.slider_text_y.set(dados["y"])
        self.slider_font_size.set(dados["size"])
        self.combo_fontes.set(dados["font"])
        self.btn_cor_texto.configure(fg_color=dados["color"])

    def atualizar_params_texto(self, event=None):
        """Pega os dados dos sliders e joga no dicionário"""
        elem = self.elemento_selecionado
        self.config_textos[elem]["x"] = int(self.slider_text_x.get())
        self.config_textos[elem]["y"] = int(self.slider_text_y.get())
        self.config_textos[elem]["size"] = int(self.slider_font_size.get())
        self.agendar_render()

    def mudar_fonte_atual(self, escolha):
        self.config_textos[self.elemento_selecionado]["font"] = escolha
        self.agendar_render()

    def escolher_cor_texto(self):
        cor = colorchooser.askcolor(title=f"Cor para {self.elemento_selecionado}")[1]
        if cor:
            self.config_textos[self.elemento_selecionado]["color"] = cor
            self.atualizar_controles_ui()
            self.agendar_render()

    def resetar_posicao(self):
        """Volta o texto para o centro"""
        defaults = {"ALUNO": -120, "MATÉRIA": 0, "TURMA": 120}
        self.config_textos[self.elemento_selecionado]["x"] = 0
        self.config_textos[self.elemento_selecionado]["y"] = defaults.get(self.elemento_selecionado, 0)
        self.atualizar_controles_ui()
        self.agendar_render()

    # --- GERENCIAMENTO DE FONTES ---
    
    def atualizar_lista_fontes(self):
        """Lê a pasta de fontes e atualiza o combobox"""
        fontes = glob.glob(os.path.join(PASTA_FONTES, "*.ttf"))
        nomes = [os.path.basename(f) for f in fontes]
        
        # Adiciona fontes padrão do sistema se não tiver nada
        if not nomes:
            nomes = ["arial.ttf", "arialbd.ttf"]
        
        self.combo_fontes.configure(values=nomes)
        
        # Garante que a fonte atual existe na lista
        atual = self.config_textos[self.elemento_selecionado]["font"]
        if atual not in nomes and nomes:
            self.config_textos[self.elemento_selecionado]["font"] = nomes[0]

    def importar_fonte(self):
        """Copia um arquivo .ttf para a pasta do projeto"""
        caminho = filedialog.askopenfilename(filetypes=[("Fontes TrueType", "*.ttf")])
        if caminho:
            try:
                shutil.copy(caminho, PASTA_FONTES)
                self.atualizar_lista_fontes()
                
                # Seleciona automaticamente a nova fonte
                novo_nome = os.path.basename(caminho)
                self.config_textos[self.elemento_selecionado]["font"] = novo_nome
                self.atualizar_controles_ui()
                self.agendar_render()
                print(f"Fonte {novo_nome} importada com sucesso!")
            except Exception as e:
                print(f"Erro ao importar fonte: {e}")

    # --- RENDERIZAÇÃO (ENGINE GRÁFICA) ---

    def renderizar_preview(self, materia_exemplo="MATÉRIA"):
        if not self.img_original: return

        # 1. Base Transparente
        base = Image.new("RGBA", (LARGURA_BASE, ALTURA_BASE), (0,0,0,0))
        
        # 2. Imagem de Fundo (Com Zoom e Drag)
        w = int(self.img_original.width * self.bg_zoom)
        h = int(self.img_original.height * self.bg_zoom)
        
        filtro = Image.Resampling.NEAREST if w > 3000 else Image.Resampling.LANCZOS
        try:
            img_resized = self.img_original.resize((w, h), filtro)
        except: return 

        # Centralização + Offset do usuário
        x_bg = (LARGURA_BASE - w)//2 + self.bg_offset_x
        y_bg = (ALTURA_BASE - h)//2 + self.bg_offset_y
        base.paste(img_resized, (x_bg, y_bg))

        # 3. Desenhar Textos (Iterando sobre a configuração)
        draw = ImageDraw.Draw(base)
        
        for chave, dados in self.config_textos.items():
            texto_final = dados["text"]
            if not texto_final and chave == "ALUNO": texto_final = "NOME DO ALUNO"
            if not texto_final and chave == "TURMA": texto_final = "TURMA / SÉRIE"
            if chave == "MATÉRIA": texto_final = materia_exemplo # A matéria varia

            self.desenhar_elemento_texto(draw, texto_final, dados)

        # Borda de visualização
        draw.rectangle([0,0, LARGURA_BASE-1, ALTURA_BASE-1], outline="white", width=2)

        # 4. Exibir
        self.exibir_no_canvas(base)

    def desenhar_elemento_texto(self, draw, texto, dados):
        """Desenha um único elemento baseado em seus dados (x, y, size, font)"""
        texto = texto.upper()
        tamanho = dados["size"]
        
        # Tenta carregar fonte
        try:
            caminho_fonte = os.path.join(PASTA_FONTES, dados["font"])
            if os.path.exists(caminho_fonte):
                font = ImageFont.truetype(caminho_fonte, tamanho)
            else:
                font = ImageFont.truetype("arialbd.ttf", tamanho) # Fallback
        except:
            font = ImageFont.load_default()

        # Calcula posição: Centro da Imagem + Offset do Usuário
        bbox = draw.textbbox((0, 0), texto, font=font)
        w_text = bbox[2] - bbox[0]
        h_text = bbox[3] - bbox[1]
        
        x_centro = (LARGURA_BASE - w_text) // 2
        y_centro = (ALTURA_BASE - h_text) // 2 # Centralização vertical base
        
        x_final = x_centro + dados["x"]
        y_final = y_centro + dados["y"]

        # Sombra (Contraste)
        cor_principal = dados["color"]
        # Define cor da sombra automática
        cor_sombra = "#000000" if cor_principal.lower() > "#aaaaaa" else "#FFFFFF"
        
        adj = 3 # Espessura sombra
        for dx in range(-adj, adj+1):
            for dy in range(-adj, adj+1):
                if dx != 0 or dy != 0:
                    draw.text((x_final+dx, y_final+dy), texto, font=font, fill=cor_sombra)
        
        draw.text((x_final, y_final), texto, font=font, fill=cor_principal)

    def exibir_no_canvas(self, pil_image):
        """Ajusta a imagem para caber no canvas da tela"""
        canvas_w = self.canvas_preview.winfo_width()
        canvas_h = self.canvas_preview.winfo_height()
        if canvas_w < 10: canvas_w = 600
        if canvas_h < 10: canvas_h = 300

        ratio = min(canvas_w/LARGURA_BASE, canvas_h/ALTURA_BASE)
        new_w = int(LARGURA_BASE * ratio) - 20
        new_h = int(ALTURA_BASE * ratio) - 20
        
        img_display = pil_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self.tk_image = ImageTk.PhotoImage(img_display)
        
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(canvas_w//2, canvas_h//2, image=self.tk_image)

    # --- LÓGICA DE EVENTOS (AGENDAR RENDER) ---
    def agendar_render(self, event=None, delay=200):
        if self.job_render: self.after_cancel(self.job_render)
        self.job_render = self.after(delay, lambda: self.renderizar_preview("MATÉRIA"))

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.bg_offset_x += dx
        self.bg_offset_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.agendar_render(delay=10)

    def on_zoom(self, event):
        fator = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
        self.bg_zoom *= fator
        self.agendar_render(delay=50)

    # --- UPLOAD E CATALOGO ---
    def upload_imagem(self):
        path = filedialog.askopenfilename(filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")])
        if path: self.carregar_imagem_base(path)

    def carregar_imagem_base(self, path):
        try:
            self.img_original = Image.open(path).convert("RGBA")
            self.bg_zoom = 1.0
            self.bg_offset_x = 0
            self.bg_offset_y = 0
            self.agendar_render()
        except Exception as e: print(e)

    def carregar_catalogo(self):
        for w in self.scroll_imgs.winfo_children(): w.destroy()
        imgs = glob.glob(os.path.join(PASTA_TEMAS, "*.jpg")) + glob.glob(os.path.join(PASTA_TEMAS, "*.png"))
        for path in imgs:
            try:
                pil = Image.open(path); pil.thumbnail((100,50))
                ctk_img = ctk.CTkImage(pil, size=(100,50))
                ctk.CTkButton(self.scroll_imgs, text=os.path.basename(path)[:10], image=ctk_img, compound="top", 
                              fg_color="transparent", command=lambda p=path: self.carregar_imagem_base(p)).pack(pady=5, fill="x")
            except: pass

    # --- GERAÇÃO PDF ---
    def iniciar_geracao_pdf(self):
        if not self.img_original: return
        self.barra_progresso.pack(fill="x"); self.barra_progresso.start()
        self.btn_gerar.configure(state="disabled")
        threading.Thread(target=self.processar_pdf).start()

    def processar_pdf(self):
        materias = self.txt_materias.get("0.0", "end").strip().split('\n')
        filename = f"Etiquetas_Custom_{self.entry_nome.get() or 'Aluno'}.pdf"
        
        c = canvas.Canvas(filename, pagesize=A4)
        w_pdf, h_pdf = 90*mm, 45*mm
        
        # Renderização Interna (Replicar lógica visual)
        for i, mat in enumerate(materias):
            if not mat: continue
            
            # Recria a imagem em memória (Full Resolution)
            base = Image.new("RGBA", (LARGURA_BASE, ALTURA_BASE), (0,0,0,0))
            w = int(self.img_original.width * self.bg_zoom)
            h = int(self.img_original.height * self.bg_zoom)
            try: img_res = self.img_original.resize((w, h), Image.Resampling.LANCZOS)
            except: img_res = self.img_original
            
            x = (LARGURA_BASE - w)//2 + self.bg_offset_x
            y = (ALTURA_BASE - h)//2 + self.bg_offset_y
            base.paste(img_res, (x, y))
            
            draw = ImageDraw.Draw(base)
            
            # Desenha cada texto configurado
            for chave, dados in self.config_textos.items():
                txt = dados["text"]
                if chave == "ALUNO" and not txt: txt = "ALUNO"
                if chave == "TURMA" and not txt: txt = "TURMA"
                if chave == "MATÉRIA": txt = mat
                self.desenhar_elemento_texto(draw, txt, dados)

            draw.rectangle([0,0, LARGURA_BASE-1, ALTURA_BASE-1], outline="black", width=2)
            
            temp = f"temp_{i}.png"
            base.save(temp)
            
            # Posição no PDF
            col = i % 2
            row = (i // 2) % 6
            x_pos = 10*mm + (col * (w_pdf + 5*mm))
            y_pos = 297*mm - 20*mm - ((row+1) * (h_pdf + 5*mm))
            
            c.drawImage(temp, x_pos, y_pos, width=w_pdf, height=h_pdf)
            os.remove(temp)
            
            if col == 1 and row == 5: c.showPage()
        
        c.save()
        os.startfile(filename)
        self.barra_progresso.stop(); self.barra_progresso.pack_forget()
        self.btn_gerar.configure(state="normal")

if __name__ == "__main__":
    app = AppEtiquetasV4()
    app.mainloop()