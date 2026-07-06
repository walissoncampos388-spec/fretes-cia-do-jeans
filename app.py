import streamlit as st
import pandas as pd

# Configuração da página web
st.set_page_config(page_title="Consulta de Fretes - Cia do Jeans", page_icon="🚚", layout="wide")

st.title("🚚 Painel de Consulta de Fretes Automática")
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
    st.error(f"Erro ao estruturar banco de dados: {e}")
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

# Só roda se o usuário realmente selecionou uma cidade e um estado válidos
if cidade_selecionada and uf_selecionada:
    resultados = df_fretes[(df_fretes['CIDADE'] == cidade_selecionada) & (df_fretes['UF'] == uf_selecionada)]
    
    if not resultados.empty:
        st.subheader(f"📍 Opções encontradas para {cidade_selecionada} - {uf_selecionada}")
        
        for idx, row in resultados.iterrows():
            with st.container():
                st.markdown(f"### 🚚 {row['TRANSPORTADORA']}")
                
                # Correção segura exibindo strings limpas
                prazo_texto = str(row['PRAZO'])
                if "cotar" not in prazo_texto.lower() and "dias" not in prazo_texto.lower() and prazo_texto != '-':
                    prazo_texto = f"{prazo_texto} Dias"

                # Cria visual em formato de tabela organizada para o usuário na tela
                st.write(f"**Rota/Envio:** {row['ROTA_ENVIO']} | **Contato:** {row['FONE']} | **Prazo:** {prazo_texto} | **Tipo:** {row['TIPO_FRETE']} | **NF:** {row['EXIGE_NF']} | **Mínimo:** {row['VALOR_MINIMO']}")
                
                texto_whatsapp = (
                    f"*FRETE PARA {cidade_selecionada.upper()}-{uf_selecionada.upper()}*\n"
                    f"🚚 TRANSPORTADORA: {row['TRANSPORTADORA']}\n"
                    f"📍 ROTA/ENVIO: {row['ROTA_ENVIO']}\n"
                    f"📆 PRAZO DE ENTREGA: {prazo_texto.upper()}\n"
                    f"📄 EXIGE NF: {row['EXIGE_NF']}\n"
                    f"💵 VALOR MÍNIMO R$: {row['VALOR_MINIMO']}"
                )
                
                st.text_area("📋 Texto Pronto para o WhatsApp:", value=texto_whatsapp, height=140, key=f"txt_{idx}")
                st.markdown("---")
    else:
        st.warning("Nenhuma transportadora encontrada para essa combinação.")
