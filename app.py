import streamlit as st
import pandas as pd
import requests
import urllib.parse

# 1. Configuração de Design da Página
st.set_page_config(
    page_title="Cia do Jeans - Calculadora Inteligente", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS Premium para forçar o Banner a colar nas bordas laterais e do topo
st.markdown("""
    <style>
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        .main { background-color: #f4f6f9; }
        
        /* Remove completamente os espaços e margens do Streamlit no topo e laterais para o Banner */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
        }
        
        /* Garante que o conteúdo abaixo do banner tenha margem nas laterais para não grudar na tela */
        .conteudo-pagina {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Blocos organizadores das etapas */
        .bloco-etapa {
            background-color: white;
            padding: 22px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            margin-bottom: 20px;
            border-top: 4px solid #1e3a8a;
        }
        .titulo-etapa {
            color: #1e3a8a;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            font-family: 'Segoe UI', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Cards de exibição do frete final */
        .card-frete {
            background-color: white;
            padding: 18px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
""", unsafe_allow_html=True)


# CACHE ULTRA-RÁPIDO: Organização inteligente e limpa da nova planilha
@st.cache_data(ttl=3600)
def carregar_e_limpar_dados():
    try:
        df = pd.read_excel("SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx", sheet_name='Plan1')
    except Exception:
        return pd.DataFrame()
        
    # Limpa cabeçalhos removendo espaços duplos invisíveis que vieram na nova planilha
    df.columns = [" ".join(str(c).split()).strip().upper() for c in df.columns]
    
    # Mapeamento exato corrigindo os nomes com ou sem "S" da sua planilha nova
    pares = [
        ('TRANSPORTADORA', 'ENVIO', 'FONE', 'PRAZO', 'FRETE', 'NF', 'VALOR MINIMO A PARTIR DE'),
        ('TRANPORTADORA 2', 'ENVIO 2', 'FONE 2', 'PRAZO 2', 'FRETE 2', 'NF 2', 'VALOR MINIMO 2'),
        ('TRANSPORTADORA 3', 'ENVIO 3', 'FONE 3', 'PRAZO 3', 'FRETE 3', 'NF 3', 'VALOR 3'),
        ('TRANSPORTADORA 4', 'ENVIO 4', 'FONE 4', 'PRAZO 4', 'FRETE 4', 'NF 4', 'VALOR 4'),
        ('TRANSPORTADORA 5', 'ENVIO 5', 'FONE 5', 'PRAZO 5', 'FRETE 5', 'NF 5', 'VALOR 5'),
        ('TRANSPORTADORA 6', 'ENVIO 6', 'FONE2', 'PRAZO 6', 'FRETE 6', 'NF 6', 'VALOR 6'),
        ('TRANSPORTADORA 7', 'ENVIO 7', 'FONE 7', 'PRAZO 7', 'FRETE 7', 'NF 7', 'VALOR MINIMO 7')
    ]
    
    cidade_col = [c for c in df.columns if 'CIDADE' in c][0] if any('CIDADE' in c for c in df.columns) else None
    uf_col = [c for c in df.columns if 'UF' in c][0] if any('UF' in c for c in df.columns) else None
    
    if not cidade_col or not uf_col:
        return pd.DataFrame()
        
    linhas = []
    for _, r in df.iterrows():
        cidade = str(r[cidade_col]).strip().upper()
        uf = str(r[uf_col]).strip().upper()
        if not cidade or cidade in ['NAN', '-', ''] or uf in ['NAN', '-', '']:
            continue
            
        for t_col, env_col, fon_col, prz_col, frt_col, nf_col, val_col in pares:
            def buscar(nome):
                # Busca flexível ignorando espaços extras entre as palavras
                nome_limpo = "".join(nome.split())
                for c in df.columns:
                    if "".join(c.split()) == nome_limpo:
                        val = r[c]
                        return str(val).strip() if pd.notna(val) else '-'
                return '-'
                
            t_name = buscar(t_col)
            if t_name and t_name not in ['-', '0', 'NAN', '']:
                linhas.append({
                    'CIDADE': cidade, 'UF': uf, 'TRANSPORTADORA': t_name,
                    'ROTA_ENVIO': buscar(env_col), 'FONE': buscar(fon_col),
                    'PRAZO': buscar(prz_col), 'TIPO_FRETE': buscar(frt_col),
                    'EXIGE_NF': buscar(nf_col), 'VALOR_MINIMO': buscar(val_col)
                })
    return pd.DataFrame(linhas)

df_fretes_fixos = carregar_e_limpar_dados()

# ==========================================
# BANNER RETANGULAR PONTA A PONTA
# ==========================================
LINK_DO_BANNER = "https://github.com/walissoncampos/fretes-cia-do-jeans/blob/main/logo_ciadojeans.png?raw=true"

try:
    st.image(LINK_DO_BANNER, use_container_width=True)
except Exception:
    st.error("⚠️ Não foi possível carregar a imagem do banner. Verifique o arquivo no GitHub.")


# ==========================================
# ENCAPSULAMENTO DO CONTEÚDO (MARGENS PRESERVADAS)
# ==========================================
st.markdown('<div class="conteudo-pagina">', unsafe_allow_html=True)

# PASSO 1: LOCALIZAÇÃO DO CLIENTE
st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
st.markdown('<div class="titulo-etapa">📍 PASSO 1: Destino do Pedido</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1.5, 2, 1])

with col1:
    cep_input = st.text_input("📬 Digite o CEP do Cliente:", placeholder="00000000", max_chars=9)

cidade_val = ""
uf_val = ""
desabilitar_campos = True

if cep_input:
    cep_limpo = cep_input.replace("-", "").replace(" ", "")
    if len(cep_limpo) == 8 and cep_limpo.isdigit():
        try:
            url_api = f"https://opencep.com/v1/{cep_limpo}"
            resposta = requests.get(url_api, timeout=3).json()
            if "localidade" in resposta:
                cidade_val = resposta.get("localidade", "").upper()
                uf_val = resposta.get("uf", "").upper()
            else:
                desabilitar_campos = False
        except Exception:
            desabilitar_campos = False

with col2: 
    cidade_automatica = st.text_input("📍 Cidade Identificada:", value=cidade_val, placeholder="Digite a Cidade se não buscar...", disabled=desabilitar_campos)
with col3: 
    uf_automatica = st.text_input("🏳️ UF:", value=uf_val, placeholder="EX: GO", disabled=desabilitar_campos)
st.markdown('</div>', unsafe_allow_html=True)

# PASSO 2: ENTRADA DE PRODUTOS
st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
st.markdown('<div class="titulo-etapa">👖 PASSO 2: O que estamos enviando hoje?</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    qtd_calcas = st.number_input("Quantidade de Calças:", min_value=0, value=0, step=1)
    qtd_bermudas = st.number_input("Quantidade de Bermudas:", min_value=0, value=0, step=1)
    qtd_shorts = st.number_input("Quantidade de Shorts:", min_value=0, value=0, step=1)
with c2:
    qtd_gola_o = st.number_input("Quantidade de Gola O:", min_value=0, value=0, step=1)
    qtd_tshirt = st.number_input("Quantidade de T-Shirt:", min_value=0, value=0, step=1)
    qtd_polo = st.number_input("Quantidade de Gola Polo:", min_value=0, value=0, step=1)

# Matemática de Pesos e Embalagem
peso_pecas_puro = (qtd_calcas * 0.60) + (qtd_bermudas * 0.40) + (qtd_shorts * 0.35) + (qtd_gola_o * 0.28) + (qtd_tshirt * 0.20) + (qtd_polo * 0.32)
peso_total_calculado = peso_pecas_puro + (0.4 if peso_pecas_puro > 0 else 0)
total_pecas = qtd_calcas + qtd_bermudas + qtd_shorts + qtd_gola_o + qtd_tshirt + qtd_polo

if total_pecas == 0: tipo_embalagem = "Nenhum produto"
elif total_pecas <= 15: tipo_embalagem = "Caixa Pequena"
elif total_pecas <= 30: tipo_embalagem = "Caixa Média"
else: tipo_embalagem = "Fardo Comercial"

valor_nf_meia = (qtd_calcas * 40) + (qtd_bermudas * 33) + (qtd_shorts * 33) + (qtd_gola_o * 18) + (qtd_tshirt * 19) + (qtd_polo * 25)

with c3:
    valor_manual_nf_txt = st.text_input("✍️ Valor Real da NF (Opcional):", placeholder="Ex: 1250,00").strip()
    
    valor_manual_nf = 0.0
    if valor_manual_nf_txt:
        try:
            valor_manual_nf = float(valor_manual_nf_txt.replace(".", "").replace(",", "."))
        except ValueError:
            st.error("⚠️ Digite um valor numérico válido para a NF.")
            
    valor_para_seguro = valor_manual_nf if valor_manual_nf > 0 else valor_nf_meia
    
    st.info(f"**📊 Resumo do Pedido:**\n* **Carga:** {total_pecas} un | {peso_total_calculado:.2f} kg\n* **Embalagem:** {tipo_embalagem}\n* **Seguro:** R$ {valor_para_seguro:.2f}")
st.markdown('</div>', unsafe_allow_html=True)

# DISPARADOR DE CÁLCULO
st.markdown("<br>", unsafe_allow_html=True)
btn_calcular = st.button("🚀 CALCULAR FRETE E GERAR WHATSAPP", type="primary", use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)

# PASSO 3: RESULTADOS E WHATSAPP
if btn_calcular:
    cidade_busca = cidade_automatica.strip().upper()
    uf_busca = uf_automatica.strip().upper()
    
    if not cep_input or not cidade_busca:
        st.error("❌ Por favor, informe um CEP válido no Passo 1.")
    elif total_pecas == 0:
        st.error("❌ Insira a quantidade de produtos no Passo 2 para calcular.")
    else:
        st.markdown("### 🏁 Transportadoras Encontradas para a Região")
        
        opcoes_whatsapp = []
        
        if df_fretes_fixos.empty:
            st.warning("⚠️ Planilha 'SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx' não encontrada.")
        else:
            resultados_fixos = df_fretes_fixos[(df_fretes_fixos['CIDADE'] == cidade_busca) & (df_fretes_fixos['UF'] == uf_busca)]
            
            if not resultados_fixos.empty:
                for idx, row in resultados_fixos.iterrows():
                    print_prazo = str(row['PRAZO'])
                    if "cotar" not in print_prazo.lower() and "dias" not in print_prazo.lower() and print_prazo != '-': 
                        print_prazo = f"{print_prazo} Dias"
                        
                    st.markdown(f"""
                    <div class="card-frete" style="border-left: 5px solid #1e3a8a;">
                        <div>
                            <strong style="font-size:16px; color:#1e3a8a;"><b> Merino 🚛 {row['TRANSPORTADORA']}</b></strong><br>
                            <span style="font-size:13px; color:#4b5563;">📍 Rota: {row['ROTA_ENVIO']} | 📞 Fone: {row['FONE']}</span><br>
                            <span style="font-size:12px; color:#6b7280;">⏱️ Prazo: {print_prazo} | 📄 Exige NF: {row['EXIGE_NF']}</span>
                        </div>
                        <div style="text-align: right;"><span style="font-size:13px; color:#6b7280; font-weight:600;">Mínimo</span><br><span style="font-size:18px; font-weight:700; color:#111827;">R$ {row['VALOR_MINIMO']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    opcoes_whatsapp.append(
                        f"🚛 *{row['TRANSPORTADORA']}*\n"
                        f"💰 Mínimo: R$ {row['VALOR_MINIMO']}\n"
                        f"⏱️ Prazo: {print_prazo}\n"
                        f"📞 Contato: {row['FONE']}\n"
                    )
            else: 
                st.warning(f"Nenhuma transportadora cadastrada no Excel regional para {cidade_busca}-{uf_busca}.")

        # PASSO 4: ENVIAR PARA O WHATSAPP
        if opcoes_whatsapp:
            st.markdown("<br><hr style='border-top: 1px dashed #cbd5e1;'><br>", unsafe_allow_html=True)
            st.markdown('<div class="bloco-etapa" style="border-top: 4px solid #25d366;">', unsafe_allow_html=True)
            st.markdown('<div class="titulo-etapa" style="color: #25d366;">💬 PASSO 3: Enviar Cotação ao Cliente</div>', unsafe_allow_html=True)
            
            texto_opcoes = "\n".join(opcoes_whatsapp)
            
            mensagem_vendedor = (
                f"Olá! Segue a cotação de frete para o seu pedido da *Cia do Jeans*:\n\n"
                f"📍 *Destino:*\n{cidade_busca} - {uf_busca}\n\n"
                f"📦 *Volume estimado:*\n{total_pecas} peças ({peso_total_calculado:.2f} kg)\n\n"
                f"🛍️ *Embalagem:*\n{tipo_embalagem}\n\n"
                f"-----------------------------------------\n"
                f"🚚 *OPÇÕES DE ENVIO:*\n\n"
                f"{texto_opcoes}"
                f"-----------------------------------------\n\n"
                f"_Qual destas opções fica melhor para fazermos o despacho?_"
            )
            
            texto_editavel = st.text_area("Pré-visualização da Mensagem:", value=mensagem_vendedor, height=250)
            texto_codificado = urllib.parse.quote(texto_editavel)
            link_whatsapp = f"https://api.whatsapp.com/send?text={texto_codificado}"
            
            st.markdown(f"""
                <a href="{link_whatsapp}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25d366; color: white; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 10px rgba(37,211,102,0.3); cursor: pointer;">
                        📲 ENVIAR COTAÇÃO PARA O WHATSAPP DO CLIENTE
                    </div>
                </a>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # Fecha a div conteudo-pagina
