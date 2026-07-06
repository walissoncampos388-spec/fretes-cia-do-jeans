import streamlit as st
import pandas as pd
import os

# 1. Configuração de Design da Página
st.set_page_config(
    page_title="Cia do Jeans - Sistema de Fretes", 
    page_icon="👖", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS personalizada para integrar a logo e ajustar as cores
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        
        /* Banner do Topo */
        .header-banner {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 20px;
            border-radius: 12px;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Cards das Transportadoras */
        .transportadora-card {
            background-color: white;
            padding: 25px;
            border-radius: 10px;
            border-left: 6px solid #1e3a8a;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        
        .info-label { font-weight: bold; color: #4b5563; }
        .info-value { color: #111827; }
    </style>
""", unsafe_allow_html=True)

# Exibição do Cabeçalho com a Logo Oficial
with st.container():
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        # Puxa a imagem diretamente usando a URL pública da imagem do GitHub de forma segura
        st.image("logo_ciadojeans.png", width=160)
            
    with col_titulo:
        st.markdown("""
            <div style="padding-top: 10px;">
                <h1 style="color: #1e3a8a; margin: 0; font-size: 34px; font-family: 'Segoe UI', sans-serif;">CIA DO JEANS</h1>
                <p style="margin: 5px 0 0 0; color: #4b5563; font-size: 16px; font-weight: 500;">SISTEMA INTELIGENTE DE CONSULTA DE FRETES</p>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx", sheet_name='Plan1')
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    pares_transportadoras = [
        ('TRANSPORTADORA', 'ENVIO', 'FONE', 'PRAZO', 'FRETE', 'NF', 'VALOR MINIMO A PARTIR DE'),
        ('TRANPORTADORA 2', 'ENVIO 2', 'FONE 2', 'PRAZO 2', 'FRETE 2', 'NF 2', 'VALOR MINIMO 2'),
        ('TRANSPORTADORA 3', 'ENVIO 3', 'FONE 3', 'PRAZO 3', 'FRETE 3', 'NF 3', 'VALOR 3'),
        ('TRANSPORTADORA 4', 'ENVIO 4', 'FONE 4', 'PRAZO 4', 'FRETE 4', 'NF 4', 'VALOR 4'),
        ('TRANSPORTADORA 5', 'ENVIO 5', 'FONE 5', 'PRAZO 5', 'FRETE 5', 'NF 5', 'VALOR 5'),
        ('TRANSPORTADORA 6', 'ENVIO 6', 'FONE2', 'PRAZO 6', 'FRETE 6', 'NF 6', 'VALOR 6'),
        ('TRANSPORTADORA 7', 'ENVIO 7', 'FONE 7', 'PRAZO 7', 'FRETE 7', 'NF 7', 'VALOR MINIMO 7')
    ]
    
    linhas_normalizadas = []
    cidade_col = 'CIDADE' if 'CIDADE' in df.columns else df.columns[1]
    uf_col = 'UF' if 'UF' in df.columns else df.columns[2]

    for _, r in df.iterrows():
        cidade = str(r[cidade_col]).strip()
        uf = str(r[uf_col]).strip()
        
        if cidade.lower() == 'nan' or not cidade:
            continue
            
        for t_col, env_col, fon_col, prz_col, frt_col, nf_col, val_col in pares_transportadoras:
            def obter_valor(nome_padrao):
                for col_real in df.columns:
                    if col_real.replace(" ", "") == nome_padrao.replace(" ", ""):
                        val = r[col_real]
                        return str(val).strip() if pd.notna(val) else '-'
                return '-'

            t_name = obter_valor(t_col)
            if t_name and t_name != '-' and t_name != '0' and t_name.lower() != 'nan':
                linhas_normalizadas.append({
                    'CIDADE': cidade,
                    'UF': uf,
                    'TRANSPORTADORA': t_name,
                    'ROTA_ENVIO': obter_valor(env_col),
                    'FONE': obter_valor(fon_col),
                    'PRAZO': obter_valor(prz_col),
                    'TIPO_FRETE': obter_valor(frt_col),
                    'EXIGE_NF': obter_valor(nf_col),
                    'VALOR_MINIMO': obter_valor(val_col)
                })
                
    return pd.DataFrame(linhas_normalizadas)

try:
    df_fretes = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar banco de dados da Cia do Jeans: {e}")
    st.stop()

# Área de Filtros organizada lado a lado com design clean
st.markdown("### 🔍 O que você deseja buscar hoje?")
col1, col2 = st.columns(2)

with col1:
    lista_cidades = sorted(df_fretes['CIDADE'].unique())
    cidade_selecionada = st.selectbox("📍 Digite ou selecione a Cidade:", [""] + lista_cidades)

with col2:
    if cidade_selecionada:
        estados_disponiveis = sorted(df_fretes[df_fretes['CIDADE'] == cidade_selecionada]['UF'].unique())
        uf_selecionada = st.selectbox("🏳️ Selecione o Estado (UF):", estados_disponiveis)
    else:
        uf_selecionada = st.selectbox("🏳️ Selecione o Estado (UF):", [""])

st.markdown("<br>", unsafe_allow_html=True)

# Apresentação Premium dos Resultados
if cidade_selecionada and uf_selecionada:
    resultados = df_fretes[(df_fretes['CIDADE'] == cidade_selecionada) & (df_fretes['UF'] == uf_selecionada)]
    
    if not resultados.empty:
        st.markdown(f"#### 📦 Encontramos {len(resultados)} opção(ões) de frete para **{cidade_selecionada.upper()} - {uf_selecionada.upper()}**:")
        
        for idx, row in resultados.iterrows():
            prazo_texto = str(row['PRAZO'])
            if "cotar" not in prazo_texto.lower() and "dias" not in prazo_texto.lower() and prazo_texto != '-':
                prazo_texto = f"{prazo_texto} Dias"

            card_col1, card_col2 = st.columns([3, 2])
            
            with card_col1:
                st.markdown(f"""
                <div class="transportadora-card">
                    <h3 style="margin-top:0; color:#1e3a8a; font-size:22px;">🚚 {row['TRANSPORTADORA']}</h3>
                    <hr style="margin: 10px 0; border: 0; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 6px 0;"><span class="info-label">📍 Rota / Envio:</span> <span class="info-value">{row['ROTA_ENVIO']}</span></p>
                    <p style="margin: 6px 0;"><span class="info-label">📞 Contato:</span> <span class="info-value">{row['FONE']}</span></p>
                    <p style="margin: 6px 0;"><span class="info-label">⏱️ Prazo de Entrega:</span> <span class="info-value">{prazo_texto}</span></p>
                    <p style="margin: 6px 0;"><span class="info-label">📦 Tipo de Frete:</span> <span class="info-value">{row['TIPO_FRETE']}</span></p>
                    <p style="margin: 6px 0;"><span class="info-label">📄 Exige NF:</span> <span class="info-value">{row['EXIGE_NF']}</span></p>
                    <p style="margin: 6px 0;"><span class="info-label">💵 Valor Mínimo:</span> <span class="info-value">R$ {row['VALOR_MINIMO']}</span></p>
                </div>
                """, unsafe_allow_html=True)
            
            with card_col2:
                texto_whatsapp = (
                    f"*FRETE PARA {cidade_selecionada.upper()}-{uf_selecionada.upper()}*\n"
                    f"🚚 TRANSPORTADORA: {row['TRANSPORTADORA']}\n"
                    f"📍 ROTA/ENVIO: {row['ROTA_ENVIO']}\n"
                    f"📆 PRAZO DE ENTREGA: {prazo_texto.upper()}\n"
                    f"📄 EXIGE NF: {row['EXIGE_NF']}\n"
                    f"💵 VALOR MÍNIMO R$: {row['VALOR_MINIMO']}"
                )
                
                st.text_area("📋 Texto Pronto para WhatsApp", value=texto_whatsapp, height=185, key=f"txt_{idx}")
            
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning("Nenhuma transportadora cadastrada para esta cidade na base da Cia do Jeans.")
