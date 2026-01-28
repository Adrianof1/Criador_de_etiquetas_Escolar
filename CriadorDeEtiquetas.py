import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import glob
from tkinter import filedialog
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# --- CONFIGURAÇÕES ---
PASTA_TEMAS = "temas_imagens"
LARGURA_ORIGINAL = 800
ALTURA_ORIGINAL = 400

# Cria a pasta se não existir
if not os.path.exists(PASTA_TEMAS):
    os.makedirs(PASTA_TEMAS)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class EditorEtiquetasPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gerador de Etiquetas PRO - Por Adriano Ferreira Dev")
        self.geometry("1280x720")
        
        # Variáveis de Estado da Imagem
        self.caminho_imagem_atual = None
        self.imagem_base = None # A imagem original carregada
        
        # Variáveis de Ajuste (Encaixe)
        self.zoom = 1.0
        self.pos_x = 0
        self.pos_y = 0
        
        # Variáveis de Estilo
        self.cor_texto = "#FFFFFF"
        self.fonte_atual = "arialbd.ttf" # Tenta usar Arial Bold padrão

        self.setup_ui()
        self.carregar_catalogo()

    def setup_ui(self):
        # Layout: Grid de 2 colunas principais (Controles/Galeria | Preview)
        self.grid_columnconfigure(1, weight=3) # Lado do Preview maior
        self.grid_rowconfigure(0, weight=1)

        # === PAINEL ESQUERDO (Controles e Galeria) ===
        self.painel_esq = ctk.CTkFrame(self, width=350)
        self.painel_esq.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
        
        # 1. Dados do Aluno
        ctk.CTkLabel(self.painel_esq, text="DADOS DA ETIQUETA", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.entry_nome = ctk.CTkEntry(self.painel_esq, placeholder_text="Nome do Aluno")
        self.entry_nome.pack(fill="x", padx=10, pady=5)
        self.entry_nome.bind("<KeyRelease>", self.atualizar_preview) # Atualiza ao digitar
        
        self.entry_turma = ctk.CTkEntry(self.painel_esq, placeholder_text="Turma / Série")
        self.entry_turma.pack(fill="x", padx=10, pady=5)
        self.entry_turma.bind("<KeyRelease>", self.atualizar_preview)

        # 2. Configurações Visuais
        ctk.CTkLabel(self.painel_esq, text="ESTILO DO TEXTO", font=("Arial", 12, "bold")).pack(pady=(15,5))
        
        self.btn_cor = ctk.CTkSegmentedButton(self.painel_esq, values=["Branco", "Preto", "Amarelo", "Azul"], command=self.mudar_cor)
        self.btn_cor.set("Branco")
        self.btn_cor.pack(pady=5)

        # 3. Ajustes de Imagem (O "Encaixe")
        ctk.CTkLabel(self.painel_esq, text="AJUSTE DE ENCAIXE (IMAGEM)", font=("Arial", 12, "bold")).pack(pady=(15,5))
        
        self.slider_zoom = ctk.CTkSlider(self.painel_esq, from_=0.5, to=3.0, command=self.atualizar_preview)
        self.slider_zoom.set(1.0)
        self.slider_zoom.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.painel_esq, text="Zoom", font=("Arial", 10)).pack()

        self.slider_x = ctk.CTkSlider(self.painel_esq, from_=-400, to=400, command=self.atualizar_preview)
        self.slider_x.set(0)
        self.slider_x.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.painel_esq, text="Mover Horizontal", font=("Arial", 10)).pack()

        self.slider_y = ctk.CTkSlider(self.painel_esq, from_=-200, to=200, command=self.atualizar_preview)
        self.slider_y.set(0)
        self.slider_y.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.painel_esq, text="Mover Vertical", font=("Arial", 10)).pack()

        # 4. Galeria e Upload
        ctk.CTkLabel(self.painel_esq, text="SELECIONE O FUNDO", font=("Arial", 14, "bold")).pack(pady=(20,5))
        
        self.btn_upload = ctk.CTkButton(self.painel_esq, text="📂 Carregar Imagem do PC", fg_color="#E67E22", command=self.upload_imagem)
        self.btn_upload.pack(fill="x", padx=10, pady=5)

        self.scroll_galeria = ctk.CTkScrollableFrame(self.painel_esq, label_text="Galeria de Personagens", height=200)
        self.scroll_galeria.pack(fill="both", expand=True, padx=5, pady=5)

        # === PAINEL DIREITO (Preview e Ação) ===
        self.painel_dir = ctk.CTkFrame(self)
        self.painel_dir.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

        ctk.CTkLabel(self.painel_dir, text="PRÉ-VISUALIZAÇÃO EM TEMPO REAL", font=("Arial", 20)).pack(pady=20)

        # Área da Imagem (Label que vai receber a foto)
        self.lbl_preview = ctk.CTkLabel(self.painel_dir, text="Selecione um tema...", width=600, height=300, fg_color="gray20", corner_radius=10)
        self.lbl_preview.pack(pady=20)

        # Lista de Matérias para Impressão
        ctk.CTkLabel(self.painel_dir, text="Matérias para Imprimir (Uma por linha):").pack()
        self.txt_materias = ctk.CTkTextbox(self.painel_dir, height=100, width=400)
        self.txt_materias.insert("0.0", "PORTUGUÊS\nMATEMÁTICA\nHISTÓRIA\nGEOGRAFIA\nCIÊNCIAS\nINGLÊS\nENS. RELIGIOSO\nARTES")
        self.txt_materias.pack(pady=10)

        self.btn_gerar = ctk.CTkButton(self.painel_dir, text="🖨️ GERAR PDF FINAL", font=("Arial", 18, "bold"), height=50, fg_color="#2ECC71", command=self.gerar_pdf)
        self.btn_gerar.pack(pady=20)

    def mudar_cor(self, valor):
        cores = {"Branco": "#FFFFFF", "Preto": "#000000", "Amarelo": "#F1C40F", "Azul": "#3498DB"}
        self.cor_texto = cores[valor]
        self.atualizar_preview()

    def carregar_catalogo(self):
        # Limpa galeria
        for w in self.scroll_galeria.winfo_children(): w.destroy()
        
        # Busca imagens
        extensoes = ['*.jpg', '*.jpeg', '*.png']
        arquivos = []
        for ext in extensoes:
            arquivos.extend(glob.glob(os.path.join(PASTA_TEMAS, ext)))
            
        # Adiciona botões na galeria
        for arq in arquivos:
            nome = os.path.basename(arq)
            btn = ctk.CTkButton(self.scroll_galeria, text=nome[:15], command=lambda p=arq: self.selecionar_tema(p), fg_color="gray30")
            btn.pack(pady=2, fill="x")

    def upload_imagem(self):
        caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg;*.png;*.jpeg")])
        if caminho:
            self.selecionar_tema(caminho)

    def selecionar_tema(self, caminho):
        self.caminho_imagem_atual = caminho
        try:
            self.imagem_base = Image.open(caminho).convert("RGBA")
            # Reseta os ajustes ao trocar de imagem
            self.slider_zoom.set(1.0)
            self.slider_x.set(0)
            self.slider_y.set(0)
            self.atualizar_preview()
        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")

    def renderizar_etiqueta(self, materia_texto="MATÉRIA EXEMPLO"):
        """Motor gráfico que cria a imagem final"""
        if not self.imagem_base:
            return None

        # 1. Cria base da etiqueta (800x400)
        img_final = Image.new("RGBA", (LARGURA_ORIGINAL, ALTURA_ORIGINAL), (0,0,0,0))
        
        # 2. Aplica Transformações (Zoom e Posição - Encaixe)
        # Calcula novo tamanho com base no zoom
        w_novo = int(self.imagem_base.width * self.slider_zoom.get())
        h_novo = int(self.imagem_base.height * self.slider_zoom.get())
        img_redimensionada = self.imagem_base.resize((w_novo, h_novo), Image.Resampling.LANCZOS)
        
        # Calcula posição centralizada + deslocamento dos sliders
        x_centro = (LARGURA_ORIGINAL - w_novo) // 2 + int(self.slider_x.get())
        y_centro = (ALTURA_ORIGINAL - h_novo) // 2 + int(self.slider_y.get())
        
        # Cola a imagem redimensionada na base da etiqueta (cropando o que sobrar)
        img_final.paste(img_redimensionada, (x_centro, y_centro))
        
        # 3. Desenha os Textos
        draw = ImageDraw.Draw(img_final)
        
        try:
            # Tenta fontes do sistema, senão fallback
            font_nome = ImageFont.truetype("arialbd.ttf", 60)
            font_mat = ImageFont.truetype("arialbd.ttf", 90)
            font_turma = ImageFont.truetype("arial.ttf", 50)
        except:
            font_nome = ImageFont.load_default()
            font_mat = ImageFont.load_default()
            font_turma = ImageFont.load_default()

        # Cores
        cor_fill = self.cor_texto
        # Sombra oposta para contraste (se texto branco, sombra preta)
        cor_shadow = "black" if cor_fill == "#FFFFFF" or cor_fill == "#F1C40F" else "white"

        def draw_text_centered(text, font, y):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            x = (LARGURA_ORIGINAL - text_w) // 2
            
            # Desenha contorno grosso (Stroke) para legibilidade perfeita
            adj = 3
            for dx in [-adj, 0, adj]:
                for dy in [-adj, 0, adj]:
                    draw.text((x+dx, y+dy), text, font=font, fill=cor_shadow)
            
            draw.text((x, y), text, font=font, fill=cor_fill)

        nome = self.entry_nome.get() or "NOME DO ALUNO"
        turma = self.entry_turma.get() or "TURMA"
        
        draw_text_centered(nome.upper(), font_nome, 40)
        draw_text_centered(materia_texto.upper(), font_mat, 140)
        draw_text_centered(turma.upper(), font_turma, 280)
        
        # 4. Moldura de acabamento
        draw.rectangle([10, 10, LARGURA_ORIGINAL-10, ALTURA_ORIGINAL-10], outline=cor_shadow, width=5)
        draw.rectangle([15, 15, LARGURA_ORIGINAL-15, ALTURA_ORIGINAL-15], outline=cor_fill, width=3)

        return img_final

    def atualizar_preview(self, event=None):
        if not self.imagem_base: return

        # Renderiza com uma matéria de exemplo para visualizar
        img = self.renderizar_etiqueta("MATEMÁTICA")
        
        # Converte para exibir na tela (CTkImage)
        # Reduz um pouco para caber na interface sem distorcer
        preview_size = (500, 250)
        img_preview = ctk.CTkImage(img, size=preview_size)
        
        self.lbl_preview.configure(image=img_preview, text="")

    def gerar_pdf(self):
        if not self.imagem_base: return
        
        materias = self.txt_materias.get("0.0", "end").strip().split('\n')
        if not materias: return

        filename = f"Etiquetas_{self.entry_nome.get() or 'Escola'}.pdf"
        
        # Configuração do PDF ReportLab
        c = canvas.Canvas(filename, pagesize=A4)
        width_a4, height_a4 = A4
        
        # Grid: 2 colunas, várias linhas
        w_etiqueta_pdf = 90 * mm
        h_etiqueta_pdf = 45 * mm
        margem_x = 10 * mm
        margem_y = height_a4 - 55 * mm
        
        col = 0
        
        print("Gerando PDF...")
        for mat in materias:
            if not mat.strip(): continue
            
            # 1. Renderiza a etiqueta para essa matéria específica
            pil_image = self.renderizar_etiqueta(mat)
            
            # 2. Salva temp
            temp_file = f"temp_{mat}.png"
            pil_image.save(temp_file)
            
            # 3. Desenha no PDF
            x_pos = margem_x + (col * (w_etiqueta_pdf + 5*mm))
            c.drawImage(temp_file, x_pos, margem_y, width=w_etiqueta_pdf, height=h_etiqueta_pdf)
            
            # Limpa temp
            os.remove(temp_file)
            
            # Lógica de Posição
            col += 1
            if col > 1: # Mudança de linha
                col = 0
                margem_y -= (h_etiqueta_pdf + 5*mm)
                
            # Nova página se encher
            if margem_y < 10*mm:
                c.showPage()
                margem_y = height_a4 - 55 * mm
                col = 0
        
        c.save()
        os.startfile(filename) # Abre o PDF (Windows)
        print(f"Sucesso! Arquivo {filename} gerado.")

if __name__ == "__main__":
    app = EditorEtiquetasPro()
    app.mainloop()