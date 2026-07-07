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

# Estilização CSS premium e limpa para os Cards
st.markdown("""
    <style>
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        .main { background-color: #f8f9fa; }
        .transportadora-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 6px solid #1e3a8a;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 15px;
        }
        .info-label { font-weight: bold; color: #4b5563; }
        .info-value { color: #111827; }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho Fixo com a Imagem Oficial da Nuvem
with st.container():
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        url_logo = "https://raw.githubusercontent.com/walissoncampos/fretes-cia-do-jeans/main/logo_ciadojeans.png"
        st.image(url_logo, width=150, output_format="PNG")
            
    with col_titulo:
        st.markdown("""
            <div style="padding-top: 5px;">
                <h1 style="color: #1e3a8a; margin: 0; font-size: 32px; font-family: 'Segoe UI', sans-serif;">CIA DO JEANS</h1>
                <p style="margin: 3px 0 0 0; color: #4b5563; font-size: 15px; font-weight: 500;">SISTEMA INTELIGENTE DE CONSULTA DE FRETES</p>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# CACHE ULTRA-RÁPIDO: Organização instantânea dos dados
@st.cache_data(ttl=3600)
def carregar_e_limpar_dados():
    try:
        df = pd.read_excel("SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx", sheet_name='Plan1')
    except Exception:
        return pd.DataFrame()
        
    df.columns = [str(c).strip().upper() for c in df.columns]
    
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
                for c in df.columns:
                    if c.replace(" ", "") == nome.replace(" ", ""):
                        val = r[c]
                        return str(val).strip() if pd.notna(val) else '-'
                return '-'
                
            t_name = buscar(t_col)
            if t_name and t_name not in ['-', '0', 'NAN', '']:
                linhas.append({
                    'CIDADE': cidade,
                    'UF': uf,
                    'TRANSPORTADORA': t_name,
                    'ROTA_ENVIO': buscar(env_col),
                    'FONE': buscar(fon_col),
                    'PRAZO': buscar(prz_col),
                    'TIPO_FRETE': buscar(frt_col),
                    'EXIGE_NF': buscar(nf_col),
                    'VALOR_MINIMO': buscar(val_col)
                })
                
    return pd.DataFrame(linhas)

df_fretes = carregar_e_limpar_dados()

if df_fretes.empty:
    st.error("Erro: Não foi possível carregar os dados da planilha. Verifique o arquivo Excel.")
    st.stop()

# Filtros Rápidos na Tela
st.markdown("### 🔍 O que você deseja buscar hoje?")
col1, col2 = st.columns(2)

with col1:
    lista_cidades = sorted(df_fretes['CIDADE'].unique())
    cidade_selecionada = st.selectbox("📍 Digite ou selecione a Cidade:", [""] + lista_cidades, key="cidade_box")

with col2:
    if cidade_selecionada:
        estados_disponiveis = sorted(df_fretes[df_fretes['CIDADE'] == cidade_selecionada]['UF'].unique())
        uf_selecionada = st.selectbox("🏳️ Selecione o Estado (UF):", estados_disponiveis, key="uf_box")
    else:
        uf_selecionada = st.selectbox("🏳️ Selecione o Estado (UF):", [""])

# Apresentação dos Resultados Filtrados
if cidade_selecionada and uf_selecionada:
    resultados = df_fretes[(df_fretes['CIDADE'] == cidade_selecionada) & (df_fretes['UF'] == uf_selecionada)]
    
    if not resultados.empty:
        st.markdown(f"#### 📦 Opções para **{cidade_selecionada} - {uf_selecionada}**:")
        
        for idx, row in resultados.iterrows():
            prazo = str(row['PRAZO'])
            if "cotar" not in prazo.lower() and "dias" not in prazo.lower() and prazo != '-':
                prazo = f"{prazo} Dias"

            card_col1, card_col2 = st.columns([3, 2])
            
            with card_col1:
                st.markdown(f"""
                <div class="transportadora-card">
                    <h3 style="margin-top:0; color:#1e3a8a; font-size:20px;">🚚 {row['TRANSPORTADORA']}</h3>
                    <hr style="margin: 8px 0; border: 0; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 4px 0;"><span class="info-label">📍 Rota / Envio:</span> <span class="info-value">{row['ROTA_ENVIO']}</span></p>
                    <p style="margin: 4px 0;"><span class="info-label">📞 Contato:</span> <span class="info-value">{row['FONE']}</span></p>
                    <p style="margin: 4px 0;"><span class="info-label">⏱️ Prazo:</span> <span class="info-value">{prazo}</span></p>
                    <p style="margin: 4px 0;"><span class="info-label">📦 Frete:</span> <span class="info-value">{row['TIPO_FRETE']}</span></p>
                    <p style="margin: 4px 0;"><span class="info-label">📄 Exige NF:</span> <span class="info-value">{row['EXIGE_NF']}</span></p>
                    <p style="margin: 4px 0;"><span class="info-label">💵 Mínimo:</span> <span class="info-value">R$ {row['VALOR_MINIMO']}</span></p>
                </div>
                """, unsafe_allow_html=True)
            
            with card_col2:
                texto_whatsapp = (
                    f"*FRETE PARA {cidade_selecionada}-{uf_selecionada}*\n"
                    f"🚚 TRANSPORTADORA: {row['TRANSPORTADORA']}\n"
                    f"📍 ROTA/ENVIO: {row['ROTA_ENVIO']}\n"
                    f"📆 PRAZO DE ENTREGA: {prazo.upper()}\n"
                    f"📄 EXIGE NF: {row['EXIGE_NF']}\n"
                    f"💵 VALOR MÍNIMO R$: {row['VALOR_MINIMO']}"
                )
                
                # Caixa de texto limpa
                st.text_area("📋 Texto Pronto para WhatsApp", value=texto_whatsapp, height=160, key=f"wtxt_{idx}")
                
                # O BOTÃO AZUL SEGURO: Roda isolado num bloco HTML do Streamlit para nunca quebrar as colunas
                html_botao_copiar = f"""
                <div style="width: 100%; text-align: center; margin-top: 5px;">
                    <button id="btn_{idx}" onclick="
                        navigator.clipboard.writeText(`{texto_whatsapp}`).then(function() {{
                            var el = document.getElementById('btn_{idx}');
                            el.innerText = '✅ COPIADO!';
                            el.style.backgroundColor = '#16a34a';
                            setTimeout(function() {{
                                el.innerText = '📋 COPIAR TEXTO';
                                el.style.backgroundColor = '#0066cc';
                            }}, 1500);
                        }}).catch(function() {{
                            alert('Erro ao copiar automaticamente. Use as folhas no topo da caixinha cinza.');
                        }});
                    " style="
                        width: 100%;
                        background-color: #0066cc;
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 8px;
                        cursor: pointer;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        font-family: sans-serif;
                    ">
                        📋 COPIAR TEXTO
                    </button>
                </div>
                """
                st.components.v1.html(html_botao_copiar, height=60)
                
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning("Nenhuma transportadora cadastrada para esta cidade na base da Cia do Jeans.")
