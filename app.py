import streamlit as st
import pandas as pd

# Configuração da página web
st.set_page_config(page_title="Consulta de Fretes - Cia do Jeans", page_icon="🚚", layout="wide")

st.title("🚚 Painel de Consulta de Fretes Automática")
st.markdown("---")

# Função para carregar e organizar o banco de dados (verticalizar as transportadoras)
@st.cache_data
def carregar_dados():
    df = pd.read_excel("SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx", sheet_name='Plan1')
    
    grupos = [
        {'nome': 'TRANSPORTADORA', 'envio': 'ENVIO', 'fone': 'FONE', 'prazo': 'PRAZO', 'frete': 'FRETE', 'nf': 'NF', 'valor': 'VALOR MINIMO A PARTIR DE'},
        {'nome': 'TRANPORTADORA 2', 'envio': 'ENVIO 2', 'fone': 'FONE 2', 'prazo': 'PRAZO 2', 'frete': 'FRETE 2 ', 'nf': 'NF 2', 'valor': 'VALOR MINIMO 2'},
        {'nome': 'TRANSPORTADORA 3', 'envio': 'ENVIO 3', 'fone': 'FONE 3', 'prazo': 'PRAZO 3', 'frete': 'FRETE 3', 'nf': 'NF 3', 'valor': 'VALOR 3'},
        {'nome': 'TRANSPORTADORA 4', 'envio': 'ENVIO 4', 'fone': 'FONE 4', 'prazo': 'PRAZO 4', 'frete': 'FRETE 4', 'nf': 'NF 4', 'valor': 'VALOR 4'},
        {'nome': 'TRANSPORTADORA 5', 'envio': 'ENVIO 5', 'fone': 'FONE 5', 'prazo': 'PRAZO 5', 'frete': 'FRETE 5', 'nf': 'NF 5', 'valor': 'VALOR 5'},
        {'nome': 'TRANSPORTADORA 6', 'envio': 'ENVIO 6', 'fone': 'FONE2', 'prazo': 'PRAZO 6', 'frete': 'FRETE 6', 'nf': 'NF 6', 'valor': 'VALOR 6'}
    ]
    
    linhas_normalizadas = []
    for _, r in df.iterrows():
        cidade = str(r['CIDADE']).strip()
        uf = str(r['UF']).strip()
        for g in grupos:
            if g['name'] in r and pd.notna(r[g['name']]):
                t_name = str(r[g['name']]).strip()
                if t_name and t_name != '0' and t_name.lower() != 'nan':
                    linhas_normalizadas.append({
                        'CIDADE': cidade,
                        'UF': uf,
                        'TRANSPORTADORA': t_name,
                        'ROTA_ENVIO': str(r[g['envio']]).strip() if g['envio'] in r and pd.notna(r[g['envio']]) else '-',
                        'FONE': str(r[g['fone']]).strip() if g['fone'] in r and pd.notna(r[g['fone']]) else '-',
                        'PRAZO': str(r[g['prazo']]).strip() if g['prazo'] in r and pd.notna(r[g['prazo']]) else '-',
                        'TIPO_FRETE': str(r[g['frete']]).strip() if g['frete'] in r and pd.notna(r[g['frete']]) else '-',
                        'EXIGE_NF': str(r[g['nf']]).strip() if g['nf'] in r and pd.notna(r[g['nf']]) else '-',
                        'VALOR_MINIMO': str(r[g['valor']]).strip() if g['valor'] in r and pd.notna(r[g['valor']]) else '-'
                    })
                
    return pd.DataFrame(linhas_normalizadas)

try:
    df_fretes = carregar_dados()
except Exception as e:
    st.error("Aguardando o upload do arquivo de dados 'SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx' neste repositório.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    lista_cidades = sorted(df_fretes['CIDADE'].unique())
    cidade_selecionada = st.selectbox("Digite ou selecione a Cidade:", [""] + lista_cidades)

with col2:
    if cidade_selecionada:
        estados_disponiveis = sorted(df_fretes[df_fretes['CIDADE'] == cidade_selecionada]['UF'].unique())
        uf_selecionada = st.selectbox("Selecione o Estado (UF):", estados_disponiveis)
    else:
        uf_selecionada = st.selectbox("Selecione o Estado (UF):", [""])

if cidade_selecionada and uf_selecionada:
    resultados = df_fretes[(df_fretes['CIDADE'] == cidade_selecionada) & (df_fretes['UF'] == uf_selecionada)]
    
    if not resultados.empty:
        st.subheader(f"📍 Opções encontradas para {cidade_selecionada} - {uf_selecionada}")
        
        for _, row in resultados.iterrows():
            with st.container():
                st.markdown(f"### 🚚 {row['TRANSPORTADORA']}")
                st.table(pd.DataFrame([{
                    "Rota/Envio": row['ROTA_ENVIO'],
                    "Contato": row['FONE'],
                    "Prazo": f"{row['PRAZO']} Dias",
                    "Tipo de Frete": row['TIPO_FRETE'],
                    "Exige NF": row['EXIGE_NF'],
                    "Valor Mínimo": f"R$ {row['VALOR_MINIMO']}"
                }]))
                
                texto_whatsapp = (
                    f"*FRETE PARA {cidade_selecionada.upper()}-{uf_selecionada.upper()}*\n"
                    f"🚚 TRANSPORTADORA: {row['TRANSPORTADORA']}\n"
                    f"📍 ROTA/ENVIO: {row['ROTA_ENVIO']}\n"
                    f"📆 PRAZO DE ENTREGA: {row['PRAZO']} DIAS\n"
                    f"📄 EXIGE NF: {row['EXIGE_NF']}\n"
                    f"💵 VALOR MÍNIMO R$: {row['VALOR_MINIMO']}"
                )
                
                st.text_area("📋 Texto Pronto para o WhatsApp:", value=texto_whatsapp, height=140, key=f"txt_{row['TRANSPORTADORA']}_{_}")
                st.markdown("---")
    else:
        st.warning("Nenhuma transportadora encontrada para essa combinação.")
