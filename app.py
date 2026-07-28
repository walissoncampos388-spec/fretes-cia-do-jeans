import base64
import math
import re
import urllib.parse
import pandas as pd
import requests
import streamlit as st

# Configurações do Token e CEPs de Origem
FRENET_TOKEN = st.secrets.get("FRENET_TOKEN", "")
FRENET_CEP_JARAGUA = "76320464"  # CEP de Origem Jaraguá - GO
FRENET_CEP_GOIANIA = "74000000"  # CEP de Origem Goiânia - GO (Para Jadlog)

# 1. Configuração de Design da Página
st.set_page_config(
    page_title="Cia do Jeans - Calculadora Inteligente",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# VERIFICAÇÃO DE QUERY PARAMS (SE O CLIENTE CLICOU NO LINK DIRETO)
query_params = st.query_params
rastreio_param = query_params.get("rastreio", "")
transp_param = query_params.get("transp", "J&T Express")
cliente_param = query_params.get("cliente", "")  # PARAMETRO NOME DO CLIENTE

# CONTROLE DE NAVEGAÇÃO
if "tela_ativa" not in st.session_state:
    if rastreio_param:
        st.session_state.tela_ativa = "rastreio"
    else:
        st.session_state.tela_ativa = "cotacao"

if "cidade_input_fiel" not in st.session_state:
    st.session_state["cidade_input_fiel"] = ""
if "uf_input_fiel" not in st.session_state:
    st.session_state["uf_input_fiel"] = ""
if "rastreio_gerado" not in st.session_state:
    st.session_state["rastreio_gerado"] = True if rastreio_param else False


# FUNÇÕES PARA LIMPAR OS TEXTOS DE PRE-VISUALIZACAO
def resetar_texto_whatsapp():
    if "txt_area_print" in st.session_state:
        del st.session_state["txt_area_print"]


def resetar_texto_rastreio():
    if "txt_area_rastreio" in st.session_state:
        del st.session_state["txt_area_rastreio"]


# Funções para alternar de tela e limpar rastreios antigos
def mudar_para_cotacao():
    st.session_state.tela_ativa = "cotacao"


def mudar_para_rastreio():
    st.session_state.tela_ativa = "rastreio"
    st.session_state["campo_codigo_estavel"] = ""
    st.session_state["rastreio_gerado"] = False
    resetar_texto_rastreio()


# Função de cotação via API da Frenet
def cotar_frenet(
    cep_destino, peso, comp, larg, alt, valor_declarado, num_volumes=1
):
    if not FRENET_TOKEN or FRENET_TOKEN == "SEU_TOKEN_FRENET_AQUI":
        return [], "Token não configurado"

    url = "https://api.frenet.com.br/shipping/quote"
    headers = {
        "Content-Type": "application/json",
        "token": FRENET_TOKEN,
    }

    peso_envio = max(float(peso) / float(num_volumes), 0.3)
    valor_declarado_envio = (
        float(valor_declarado) / float(num_volumes)
        if valor_declarado > 0
        else 100.0
    )

    comp_envio = max(int(comp), 16)
    larg_envio = max(int(larg), 11)
    alt_envio = max(int(alt), 4)

    servicos = []
    erros_retornados = []

    # --- 1. COTAÇÃO ORIGEM JARAGUÁ (Correios, J&T, etc.) ---
    payload_jaragua = {
        "SellerCEP": FRENET_CEP_JARAGUA,
        "RecipientCEP": str(cep_destino).replace("-", "").replace(" ", ""),
        "ShipmentInvoiceValue": valor_declarado_envio,
        "ShippingItemArray": [
            {
                "Weight": peso_envio,
                "Length": comp_envio,
                "Height": alt_envio,
                "Width": larg_envio,
                "Quantity": int(num_volumes),
            }
        ],
    }

    try:
        res1 = requests.post(
            url, json=payload_jaragua, headers=headers, timeout=6
        )
        if res1.status_code == 200:
            dados1 = res1.json()
            for op in dados1.get("ShippingSevicesArray", []):
                if not op.get("Error"):
                    nome_transp = op.get("Carrier", "").upper()
                    if "JADLOG" not in nome_transp:
                        nome_servico = op.get("ServiceDescription", "")
                        preco_raw = op.get("ShippingPrice", 0.0)
                        prazo = op.get("DeliveryTime", "-")

                        try:
                            preco_total = float(
                                str(preco_raw).replace(",", ".").strip()
                            )
                            preco_fmt = f"{preco_total:.2f}".replace(".", ",")

                            if num_volumes > 1:
                                preco_por_volume = preco_total / float(
                                    num_volumes
                                )
                                preco_vol_fmt = f"{preco_por_volume:.2f}".replace(
                                    ".", ","
                                )
                                detalhe_vol = (
                                    f"⚠️ Envio obrigatório em"
                                    f" {int(num_volumes)} volumes (acima de 30"
                                    f" kg)\n📦 Valor por volume: R$"
                                    f" {preco_vol_fmt}\n💵 Total somado"
                                    f" ({int(num_volumes)} vol.): R$"
                                    f" {preco_fmt}"
                                )
                            else:
                                detalhe_vol = ""
                        except ValueError:
                            preco_fmt = str(preco_raw)
                            detalhe_vol = ""

                        servicos.append({
                            "TRANSPORTADORA": f"{nome_transp} ({nome_servico})",
                            "VALOR_MINIMO": preco_fmt,
                            "PRAZO": f"{prazo} Dias",
                            "ROTA_ENVIO": "Origem Jaraguá - GO",
                            "FONE": "Atendimento Online",
                            "EXIGE_NF": "Sim",
                            "DETALHE_TRANSPORTE": detalhe_vol,
                        })
                else:
                    erros_retornados.append(
                        f"{op.get('Carrier')}: {op.get('Msg')}"
                    )
    except Exception as e:
        erros_retornados.append(f"Erro Jaraguá: {str(e)}")

    # --- 2. COTAÇÃO ORIGEM GOIÂNIA (Jadlog + Transbessa R$ 30,00 por Volume) ---
    payload_goiania = {
        "SellerCEP": FRENET_CEP_GOIANIA,
        "RecipientCEP": str(cep_destino).replace("-", "").replace(" ", ""),
        "ShipmentInvoiceValue": valor_declarado_envio,
        "ShippingItemArray": [
            {
                "Weight": peso_envio,
                "Length": comp_envio,
                "Height": alt_envio,
                "Width": larg_envio,
                "Quantity": int(num_volumes),
            }
        ],
    }

    try:
        res2 = requests.post(
            url, json=payload_goiania, headers=headers, timeout=6
        )
        if res2.status_code == 200:
            dados2 = res2.json()
            for op in dados2.get("ShippingSevicesArray", []):
                if not op.get("Error"):
                    nome_transp = op.get("Carrier", "").upper()
                    if "JADLOG" in nome_transp:
                        nome_servico = op.get("ServiceDescription", "")
                        preco_raw = op.get("ShippingPrice", 0.0)
                        prazo_raw = op.get("DeliveryTime", 0)

                        try:
                            val_jadlog_total = float(
                                str(preco_raw).replace(",", ".").strip()
                            )
                            taxa_transbessa_total = 30.0 * float(num_volumes)
                            total_soma_frete = (
                                val_jadlog_total + taxa_transbessa_total
                            )

                            preco_fmt = f"{total_soma_frete:.2f}".replace(
                                ".", ","
                            )

                            try:
                                prazo_total = int(prazo_raw) + 1
                            except ValueError:
                                prazo_total = f"{prazo_raw} + 1"

                            if num_volumes > 1:
                                val_jadlog_vol = val_jadlog_total / float(
                                    num_volumes
                                )
                                val_total_vol = val_jadlog_vol + 30.0

                                val_jadlog_vol_fmt = (
                                    f"{val_jadlog_vol:.2f}".replace(".", ",")
                                )
                                val_total_vol_fmt = (
                                    f"{val_total_vol:.2f}".replace(".", ",")
                                )

                                detalhe_transbessa = (
                                    f"⚠️ Envio obrigatório em"
                                    f" {int(num_volumes)} volumes (acima de 30"
                                    " kg)\n📦 Jadlog por vol.: R$"
                                    f" {val_jadlog_vol_fmt} | Transbessa por"
                                    " vol.: R$ 30,00 ➔ Total por volume: R$"
                                    f" {val_total_vol_fmt}\n💵 Total Geral"
                                    f" Somado ({int(num_volumes)} vol.): R$"
                                    f" {preco_fmt}"
                                )
                            else:
                                val_jadlog_fmt = (
                                    f"{val_jadlog_total:.2f}".replace(".", ",")
                                )
                                detalhe_transbessa = (
                                    f"📦 Cotação Jadlog: R$ {val_jadlog_fmt}\n🚚"
                                    " Transbessa (Jaraguá ➔ Goiânia): R$"
                                    " 30,00 (1 vol. x R$ 30,00 | Prazo: 1 dia)"
                                )
                        except ValueError:
                            preco_fmt = str(preco_raw)
                            detalhe_transbessa = (
                                "Inclui frete Transbessa R$ 30,00 por volume"
                            )
                            prazo_total = prazo_raw

                        servicos.append({
                            "TRANSPORTADORA": (
                                f"{nome_transp} ({nome_servico}) - via Goiânia"
                            ),
                            "VALOR_MINIMO": preco_fmt,
                            "PRAZO": f"{prazo_total} Dias",
                            "ROTA_ENVIO": "Jaraguá ➔ Goiânia ➔ Destino",
                            "FONE": "Atendimento Online",
                            "EXIGE_NF": "Sim",
                            "DETALHE_TRANSPORTE": detalhe_transbessa,
                        })
    except Exception as e:
        erros_retornados.append(f"Erro Goiânia: {str(e)}")

    msg_status = (
        "OK"
        if servicos
        else (
            "; ".join(erros_retornados)
            if erros_retornados
            else "Nenhum serviço retornado pela Frenet"
        )
    )
    return servicos, msg_status


# Estilização CSS
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #f8fafc !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: #0f172a;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1140px !important;
        }
        .bloco-etapa {
            background-color: #ffffff;
            padding: 28px;
            border-radius: 16px;
            box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
            position: relative;
            overflow: hidden;
        }
        .bloco-etapa::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        }
        .titulo-etapa {
            color: #0f172a; font-size: 16px; font-weight: 700;
            margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.6px;
        }
        .card-frete {
            background-color: #ffffff; padding: 20px 24px; border-radius: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 14px;
            display: flex; justify-content: space-between; align-items: center;
            border: 1px solid #e2e8f0;
        }
        div.stButton > button[key="trigger_calculo"], div.stButton > button[key="action_processar_rastreio"] {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
            color: white !important; font-weight: 700 !important; font-size: 16px !important;
            padding: 16px 28px !important; border-radius: 12px !important; border: none !important;
        }
        div.stButton > button[key="btn_pure_copy_frete"], div.stButton > button[key="btn_pure_copy_rastreio"] {
            background-color: #0f172a !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            padding: 14px !important;
            border-radius: 10px !important;
            border: none !important;
            width: 100% !important;
            margin-top: 8px !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def carregar_e_limpar_dados():
    try:
        df = pd.read_excel(
            "SISTEMA_DE_FRETES_AUTOMATIZADO.xlsx", sheet_name="Plan1"
        )
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip().upper() for c in df.columns]

    pares = [
        (
            "TRANSPORTADORA",
            "ENVIO",
            "FONE",
            "PRAZO",
            "FRETE",
            "NF",
            "VALOR MINIMO A PARTIR DE",
        ),
        (
            "TRANPORTADORA 2",
            "ENVIO 2",
            "FONE 2",
            "PRAZO 2",
            "FRETE 2",
            "NF 2",
            "VALOR MINIMO 2",
        ),
        (
            "TRANSPORTADORA 3",
            "ENVIO 3",
            "FONE 3",
            "PRAZO 3",
            "FRETE 3",
            "NF 3",
            "VALOR 3",
        ),
        (
            "TRANSPORTADORA 4",
            "ENVIO 4",
            "FONE 4",
            "PRAZO 4",
            "FRETE 4",
            "NF 4",
            "VALOR 4",
        ),
        (
            "TRANSPORTADORA 5",
            "ENVIO 5",
            "FONE 5",
            "PRAZO 5",
            "FRETE 5",
            "NF 5",
            "VALOR 5",
        ),
        (
            "TRANSPORTADORA 6",
            "ENVIO 6",
            "FONE2",
            "PRAZO 6",
            "FRETE 6",
            "NF 6",
            "VALOR 6",
        ),
        (
            "TRANSPORTADORA 7",
            "ENVIO 7",
            "FONE 7",
            "PRAZO 7",
            "FRETE 7",
            "NF 7",
            "VALOR MINIMO 7",
        ),
    ]

    cidade_col = (
        [c for c in df.columns if "CIDADE" in c][0]
        if any("CIDADE" in c for c in df.columns)
        else None
    )
    uf_col = (
        [c for c in df.columns if "UF" in c][0]
        if any("UF" in c for c in df.columns)
        else None
    )

    if not cidade_col or not uf_col:
        return pd.DataFrame()

    linhas = []
    for _, r in df.iterrows():
        cidade = str(r[cidade_col]).strip().upper()
        uf = str(r[uf_col]).strip().upper()
        if not cidade or cidade in ["NAN", "-", ""] or uf in ["NAN", "-", ""]:
            continue

        for t_col, env_col, fon_col, prz_col, frt_col, nf_col, val_col in pares:

            def buscar(nome):
                for c in df.columns:
                    if c.replace(" ", "") == nome.replace(" ", ""):
                        val = r[c]
                        return str(val).strip() if pd.notna(val) else "-"
                return "-"

            t_name = buscar(t_col)
            if t_name and t_name not in ["-", "0", "NAN", ""]:
                linhas.append({
                    "CIDADE": cidade,
                    "UF": uf,
                    "TRANSPORTADORA": t_name,
                    "ROTA_ENVIO": buscar(env_col),
                    "FONE": buscar(fon_col),
                    "PRAZO": buscar(prz_col),
                    "TIPO_FRETE": buscar(frt_col),
                    "EXIGE_NF": buscar(nf_col),
                    "VALOR_MINIMO": buscar(val_col),
                })
    return pd.DataFrame(linhas)


df_fretes_fixos = carregar_e_limpar_dados()


def arrumar_imagem_local(caminho):
    try:
        with open(caminho, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return ""


img_base64 = arrumar_imagem_local("logo_ciadojeans.PNG")

# Topo
st.markdown(
    f"""
    <div style='background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1e40af 100%); padding: 12px 16px; border-radius: 16px; text-align: center; margin-bottom: 24px;'>
        <img src="data:image/png;base64,{img_base64}" style="display: block; margin: 0 auto; width: 900px; max-width: 98%; height: auto; max-height: 280px; object-fit: contain;">
        <p style='color: #93c5fd; font-weight: 600; margin-top: -6px; font-size: 0.95rem; text-transform: uppercase;'>⚡ Logística & Cotação Inteligente</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# SE FOR ACESSO DE CLIENTE DIRETO VIA LINK, OCULTA OS BOTOES DE ALTERNAR TELA
if not rastreio_param:
    col_aba1, col_aba2 = st.columns(2)
    with col_aba1:
        st.button(
            "📊 COTAR NOVO FRETE",
            use_container_width=True,
            key="aba_cot_btn",
            on_click=mudar_para_cotacao,
        )
    with col_aba2:
        st.button(
            "📦 RASTREAR ENCOMENDA",
            use_container_width=True,
            key="aba_ras_btn",
            on_click=mudar_para_rastreio,
        )
    st.markdown("<br>", unsafe_allow_html=True)

# TELA COTAÇÃO
if st.session_state.tela_ativa == "cotacao" and not rastreio_param:

    # PASSO 1
    st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
    st.markdown(
        '<div class="titulo-etapa">📍 PASSO 1: Destino do Pedido</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1.5, 2, 1])

    with col1:
        cep_input = st.text_input(
            "📬 Digite o CEP do Cliente:",
            placeholder="00000000",
            max_chars=9,
            key="cep_input_fiel",
        )

    desabilitar_campos = False
    if cep_input:
        cep_limpo = cep_input.replace("-", "").replace(" ", "")
        if len(cep_limpo) == 8 and cep_limpo.isdigit():
            try:
                resposta = requests.get(
                    f"https://opencep.com/v1/{cep_limpo}", timeout=3
                ).json()
                if resposta.get("localidade"):
                    st.session_state["cidade_input_fiel"] = resposta.get(
                        "localidade", ""
                    ).upper()
                    st.session_state["uf_input_fiel"] = resposta.get(
                        "uf", ""
                    ).upper()
                    desabilitar_campos = True
            except Exception:
                pass

    with col2:
        st.text_input(
            "📍 Cidade Identificada:",
            disabled=desabilitar_campos,
            key="cidade_input_fiel",
        )
    with col3:
        st.text_input(
            "🏳️ UF:", disabled=desabilitar_campos, key="uf_input_fiel"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # PASSO 2
    st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
    st.markdown(
        '<div class="titulo-etapa">👖 PASSO 2: Produtos</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        qtd_calcas = st.number_input(
            "Quantidade de Calças:", min_value=0, value=0, key="calc_un"
        )
        qtd_bermudas = st.number_input(
            "Quantidade de Bermudas:", min_value=0, value=0, key="berm_un"
        )
        qtd_shorts = st.number_input(
            "Quantidade de Shorts:", min_value=0, value=0, key="shor_un"
        )
        qtd_camisas = st.number_input(
            "Quantidade de Camisas:", min_value=0, value=0, key="cam_un"
        )
        qtd_saias = st.number_input(
            "Quantidade de Saias:", min_value=0, value=0, key="saia_un"
        )
        qtd_croppeds = st.number_input(
            "Quantidade de Croppeds:", min_value=0, value=0, key="crop_un"
        )

    with c2:
        qtd_gola_o = st.number_input(
            "Quantidade de Gola O:", min_value=0, value=0, key="gola_un"
        )
        qtd_tshirt = st.number_input(
            "Quantidade de T-Shirt:", min_value=0, value=0, key="tsh_un"
        )
        qtd_polo = st.number_input(
            "Quantidade de Gola Polo:", min_value=0, value=0, key="polo_un"
        )
        qtd_vestidos = st.number_input(
            "Quantidade de Vestidos:", min_value=0, value=0, key="vest_un"
        )
        qtd_conjuntos = st.number_input(
            "Quantidade de Conjuntos:", min_value=0, value=0, key="conj_un"
        )
        qtd_bones = st.number_input(
            "Quantidade de Bonés:", min_value=0, value=0, key="bone_un"
        )

    peso_pecas_puro = (
        (qtd_calcas * 0.60)
        + (qtd_bermudas * 0.40)
        + (qtd_shorts * 0.35)
        + (qtd_gola_o * 0.28)
        + (qtd_tshirt * 0.20)
        + (qtd_polo * 0.32)
        + (qtd_vestidos * 0.55)
        + (qtd_conjuntos * 0.50)
        + (qtd_bones * 0.10)
        + (qtd_camisas * 0.25)
        + (qtd_saias * 0.30)
        + (qtd_croppeds * 0.15)
    )
    peso_total_calculado = peso_pecas_puro + (
        0.4 if peso_pecas_puro > 0 else 0
    )
    total_pecas = (
        qtd_calcas
        + qtd_bermudas
        + qtd_shorts
        + qtd_gola_o
        + qtd_tshirt
        + qtd_polo
        + qtd_vestidos
        + qtd_conjuntos
        + qtd_bones
        + qtd_camisas
        + qtd_saias
        + qtd_croppeds
    )

    with c3:
        valor_manual_nf_txt = st.text_input(
            "✍️ Valor Real da NF (Opcional):", key="nf_manual_txt"
        ).strip()
        valor_manual_nf = 0.0
        if valor_manual_nf_txt:
            try:
                valor_manual_nf = float(
                    valor_manual_nf_txt.replace(".", "").replace(",", ".")
                )
            except ValueError:
                pass

        meio_envio_selecionado = st.selectbox(
            "📦 Regra de Divisão:",
            [
                "Padrão (Dividir acima de 50 kg)",
                "Correios / J&T / Azul Cargo (Dividir acima de 30 kg)",
                "Não Dividir fardo",
            ],
            key="box_regra_divisao_fardo",
        )

        num_volumes = 1
        if total_pecas > 0:
            if (
                meio_envio_selecionado == "Padrão (Dividir acima de 50 kg)"
                and peso_total_calculado > 50.0
            ):
                num_volumes = math.ceil(peso_total_calculado / 50.0)
            elif (
                meio_envio_selecionado
                == "Correios / J&T / Azul Cargo (Dividir acima de 30 kg)"
                and peso_total_calculado > 30.0
            ):
                num_volumes = math.ceil(peso_total_calculado / 30.0)

        peso_por_volume = (
            peso_total_calculado / num_volumes if num_volumes > 0 else 0
        )
        pecas_por_volume = (
            math.ceil(total_pecas / num_volumes) if num_volumes > 0 else 0
        )

        if total_pecas == 0:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Nenhum produto",
                0,
                0,
                0,
                "Sem Carga",
            )
        elif pecas_por_volume <= 15:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Caixa Pequena",
                40,
                30,
                20,
                "PP (Caixa Pequena)",
            )
        elif pecas_por_volume <= 30:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Caixa Média",
                50,
                40,
                30,
                "P (Caixa Média)",
            )
        elif pecas_por_volume <= 60:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Fardo Comercial",
                60,
                45,
                35,
                "M (Fardo Padrão)",
            )
        elif pecas_por_volume <= 120:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Fardo Comercial",
                80,
                50,
                40,
                "G (Fardo Grande)",
            )
        else:
            tipo_embalagem, comp, larg, alt, classificacao_tamanho = (
                "Fardo Comercial",
                100,
                60,
                50,
                "XG (Fardo Master)",
            )

        if num_volumes >= 2 and comp > 70:
            excesso = comp - 70
            comp = 70
            larg += math.ceil(excesso / 2)
            alt += math.floor(excesso / 2)

        orientacao_texto = (
            "Fardo em Pé" if "G" in classificacao_tamanho else "Fardo Deitado"
        )

        valor_nf_calculado = (
            (qtd_calcas * 99.00)
            + (qtd_bermudas * 70.00)
            + (qtd_shorts * 79.50)
            + (qtd_camisas * 107.50)
            + (qtd_saias * 83.50)
            + (qtd_croppeds * 49.00)
            + (qtd_gola_o * 42.50)
            + (qtd_tshirt * 42.50)
            + (qtd_polo * 60.00)
            + (qtd_vestidos * 89.50)
            + (qtd_conjuntos * 110.00)
            + (qtd_bones * 47.50)
        )
        valor_para_seguro = (
            valor_manual_nf if valor_manual_nf > 0 else valor_nf_calculado
        )

        st.info(
            f"**📊 Resumo:** {total_pecas} un | {peso_total_calculado:.2f} kg |"
            f" Seguro/NF: R$ {valor_para_seguro:.2f}"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    btn_calcular = st.button(
        "🚀 CALCULAR FRETE E GERAR WHATSAPP",
        type="primary",
        use_container_width=True,
        key="trigger_calculo",
        on_click=resetar_texto_whatsapp,
    )

    if btn_calcular or st.session_state.get("frete_calculado_ok", False):
        st.session_state["frete_calculado_ok"] = True
        cidade_busca = (
            st.session_state.get("cidade_input_fiel", "").strip().upper()
        )
        uf_busca = st.session_state.get("uf_input_fiel", "").strip().upper()

        if not cidade_busca or total_pecas == 0:
            st.error(
                "❌ Preencha o CEP/Cidade e adicione produtos para calcular."
            )
        else:
            st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="titulo-etapa">📐 Dimensões e Comparativo de'
                f" Escala ({orientacao_texto})</div>",
                unsafe_allow_html=True,
            )

            v_col1, v_col2 = st.columns([1, 1.2])

            with v_col1:
                txt_vol_detalhe = (
                    "<p style='margin: 0 0 8px 0; font-size: 14px; color:"
                    " #b45309; font-weight: 600;'>⚠️ Carga Dividida:"
                    f" {num_volumes} Volumes ({meio_envio_selecionado})</p>"
                    if num_volumes > 1
                    else ""
                )
                st.html(f"""
<div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; font-family: sans-serif;">
{txt_vol_detalhe}
<p style="margin: 0 0 8px 0; font-size: 14px; color: #334155;"><b>Quantidade Total de Volumes:</b> {num_volumes} volume(s)</p>
<p style="margin: 0 0 8px 0; font-size: 14px; color: #334155;"><b>Classificação (por volume):</b> {classificacao_tamanho}</p>
<p style="margin: 0 0 8px 0; font-size: 14px; color: #334155;"><b>Peso por Volume:</b> {peso_por_volume:.2f} kg</p>
<p style="margin: 0 0 8px 0; font-size: 14px; color: #334155;"><b>Comprimento:</b> {comp} cm</p>
<p style="margin: 0 0 8px 0; font-size: 14px; color: #334155;"><b>Largura:</b> {larg} cm</p>
<p style="margin: 0 0 0 0; font-size: 14px; color: #334155;"><b>Altura:</b> {alt} cm</p>
</div>
""")

            with v_col2:
                visual_altura = (
                    comp if "G" in classificacao_tamanho else alt
                )
                visual_largura = larg
                px_alt_fardo = int(visual_altura * 1.3)
                px_larg_fardo = int(visual_largura * 1.3)

                html_fardos_render = ""
                for vol_i in range(num_volumes):
                    label_fardo = (
                        "FARDO" if num_volumes == 1 else f"VOL {vol_i+1}"
                    )
                    html_fardos_render += f"""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%;">
<div style="font-family: sans-serif; font-size: 11px; color: #1e3a8a; font-weight: bold; margin-bottom: 4px;">{comp}x{larg}x{alt} cm</div>
<div style="width: {px_larg_fardo}px; height: {px_alt_fardo}px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(217,119,6,0.3); margin-bottom: 0px;">
<span style="color: white; font-size: 10px; font-weight: bold; text-align: center; font-family: sans-serif; padding: 2px;">{label_fardo}</span>
</div>
</div>
"""

                st.html(f"""
<div style="display: flex; align-items: flex-end; justify-content: center; gap: 20px; background: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; height: 250px; overflow-x: auto;">
<div style="display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; flex-shrink: 0;">
<div style="font-family: sans-serif; font-size: 11px; color: #64748b; margin-bottom: 4px;">Pessoa (1.75m)</div>
<div style="width: 50px; height: 215px; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; margin-bottom: 0px;">
    <div style="width: 26px; height: 26px; background-color: #f3c693; border-radius: 50%; margin-bottom: 4px;"></div>
    <div style="width: 38px; height: 65px; background-color: #1e3a8a; border-radius: 4px 4px 0 0; position: relative;">
        <div style="width: 6px; height: 45px; background-color: #f3c693; position: absolute; left: -7px; top: 0; border-radius: 3px;"></div>
        <div style="width: 6px; height: 45px; background-color: #f3c693; position: absolute; right: -7px; top: 0; border-radius: 3px;"></div>
    </div>
    <div style="width: 34px; height: 105px; display: flex; justify-content: space-between;">
        <div style="width: 14px; height: 105px; background-color: #0f172a; border-radius: 0 0 2px 2px;"></div>
        <div style="width: 14px; height: 105px; background-color: #0f172a; border-radius: 0 0 2px 2px;"></div>
    </div>
</div>
</div>
{html_fardos_render}
</div>
""")
            st.markdown("</div>", unsafe_allow_html=True)

            opcoes_whatsapp = []
            cotacoes_api = []

            if cep_input:
                cotacoes_api, status_frenet = cotar_frenet(
                    cep_input,
                    peso_total_calculado,
                    comp,
                    larg,
                    alt,
                    valor_para_seguro,
                    num_volumes,
                )

                if cotacoes_api:
                    st.markdown("### ⚡ Cotação Online")
                    for item in cotacoes_api:
                        txt_detalhe_item = (
                            f"\n_{item['DETALHE_TRANSPORTE']}_"
                            if item.get("DETALHE_TRANSPORTE")
                            else ""
                        )
                        opcoes_whatsapp.append(
                            f"🚛 *{item['TRANSPORTADORA']}*\n💰 Valor:"
                            f" R$ {item['VALOR_MINIMO']}\n⏱️ Prazo:"
                            f" {item['PRAZO']}{txt_detalhe_item}\n"
                        )

                        html_detalhe = (
                            f'<br><span style="font-size:11px;'
                            f' color:#0284c7;">{item["DETALHE_TRANSPORTE"].replace(chr(10), "<br>")}</span>'
                            if item.get("DETALHE_TRANSPORTE")
                            else ""
                        )

                        st.markdown(
                            f"""
                        <div class="card-frete" style="border-left: 5px solid #2563eb;">
                            <div>
                                <strong style="font-size:16px; color:#0f172a;"><b>🚛 {item['TRANSPORTADORA']}</b></strong><br>
                                <span style="font-size:12px; color:#94a3b8;">⏱️ Prazo: {item['PRAZO']}</span>{html_detalhe}
                            </div>
                            <div style="text-align: right;"><span style="font-size:18px; font-weight:700; color:#0f172a;">R$ {item['VALOR_MINIMO']}</span></div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.warning(f"⚠️ Diagnóstico API Frenet: {status_frenet}")

            if not df_fretes_fixos.empty:
                resultados_fixos = df_fretes_fixos[
                    (df_fretes_fixos["CIDADE"] == cidade_busca)
                    & (df_fretes_fixos["UF"] == uf_busca)
                ]

                if not resultados_fixos.empty:
                    transportadoras_online = [
                        item["TRANSPORTADORA"].upper() for item in cotacoes_api
                    ]

                    resultados_filtrados = []
                    for idx, row in resultados_fixos.iterrows():
                        nome_planilha = (
                            str(row["TRANSPORTADORA"]).upper().strip()
                        )
                        ja_existe_online = any(
                            transp_api in nome_planilha
                            or nome_planilha in transp_api
                            for transp_api in transportadoras_online
                        )
                        if not ja_existe_online:
                            resultados_filtrados.append(row)

                    if resultados_filtrados:
                        st.markdown("### 🏁 Outras Transportadoras")
                        for row in resultados_filtrados:
                            nome_transp_raw = str(row["TRANSPORTADORA"]).upper().strip()
                            print_prazo = str(row["PRAZO"])
                            if (
                                "cotar" not in print_prazo.lower()
                                and "dias" not in print_prazo.lower()
                                and print_prazo != "-"
                            ):
                                print_prazo = f"{print_prazo} Dias"

                            if "CARVALIMA" in nome_transp_raw:
                                taxa_transbessa = 30.0 * float(num_volumes)

                                if peso_total_calculado <= 10.0:
                                    val_carvalima = 84.33
                                elif peso_total_calculado <= 30.0:
                                    val_carvalima = 138.39
                                elif peso_total_calculado <= 70.0:
                                    val_carvalima = 210.83
                                else:
                                    excesso_kg = peso_total_calculado - 70.0
                                    val_carvalima = 210.83 + (excesso_kg * 2.90)

                                total_bessa_carvalima = taxa_transbessa + val_carvalima

                                val_total_fmt = f"{total_bessa_carvalima:.2f}".replace(".", ",")
                                val_carvalima_fmt = f"{val_carvalima:.2f}".replace(".", ",")
                                val_bessa_fmt = f"{taxa_transbessa:.2f}".replace(".", ",")

                                html_detalhe_carvalima = (
                                    f'<br><span style="font-size:11px; color:#0284c7;">'
                                    f"🚚 Transbessa (Jaraguá ➔ Goiânia): R$ {val_bessa_fmt} ({num_volumes} vol. x R$ 30,00)<br>"
                                    f"📦 Carvalima (Goiânia ➔ Destino): R$ {val_carvalima_fmt} (Faixa para {peso_total_calculado:.2f} kg)"
                                    f"</span>"
                                )

                                st.markdown(
                                    f"""
                                <div class="card-frete" style="border-left: 5px solid #1e3a8a;">
                                    <div>
                                        <strong style="font-size:16px; color:#0f172a;"><b>🚛 {row['TRANSPORTADORA']}</b></strong><br>
                                        <span style="font-size:12px; color:#64748b;">⏱️ Prazo: {print_prazo} | 📞 Fone: {row['FONE']}</span>
                                        {html_detalhe_carvalima}
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="font-size:18px; font-weight:700; color:#0f172a;">R$ {val_total_fmt}</span>
                                    </div>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )

                                opcoes_whatsapp.append(
                                    f"🚛 *{row['TRANSPORTADORA']}*\n"
                                    f"💰 Total: R$ {val_total_fmt}\n"
                                    f"⏱️ Prazo: {print_prazo}\n"
                                    f"_(Transbessa R$ {val_bessa_fmt} + Carvalima R$ {val_carvalima_fmt})_\n"
                                )

                            else:
                                st.markdown(
                                    f"""
                                <div class="card-frete" style="border-left: 5px solid #1e3a8a;">
                                    <div>
                                        <strong style="font-size:16px; color:#0f172a;"><b>🚛 {row['TRANSPORTADORA']}</b></strong><br>
                                        <span style="font-size:13px; color:#64748b;">📍 Rota: {row['ROTA_ENVIO']} | 📞 Fone: {row['FONE']}</span><br>
                                        <span style="font-size:12px; color:#94a3b8;">⏱️ Prazo: {print_prazo} | 📄 Exige NF: {row['EXIGE_NF']}</span>
                                    </div>
                                    <div style="text-align: right;"><span style="font-size:12px; color:#64748b; font-weight:600;">Mínimo</span><br><span style="font-size:18px; font-weight:700; color:#0f172a;">R$ {row['VALOR_MINIMO']}</span></div>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )

                                opcoes_whatsapp.append(
                                    f"🚛 *{row['TRANSPORTADORA']}*\n"
                                    f"💰 Mínimo: R$ {row['VALOR_MINIMO']}\n"
                                    f"⏱️ Prazo: {print_prazo}\n"
                                    f"📞 Contato: {row['FONE']}\n"
                                )

            if opcoes_whatsapp:
                st.markdown(
                    '<div class="bloco-etapa" style="border-top-color:'
                    ' #25d366;">',
                    unsafe_allow_html=True,
                )
                texto_opcoes = "\n".join(opcoes_whatsapp)
                mensagem_vendedor = (
                    "Olá! Segue a cotação de frete para o seu pedido da *Cia do"
                    " Jeans*:\n\n"
                    f"📍 *Destino:*\n{cidade_busca} - {uf_busca}\n\n"
                    f"📦 *Volume estimado:*\n{total_pecas} peças"
                    f" ({peso_total_calculado:.2f} kg)\n\n"
                    "-----------------------------------------\n"
                    "🚚 *OPÇÕES DE ENVIO:*\n\n"
                    f"{texto_opcoes}"
                    "-----------------------------------------\n\n"
                    "_Qual destas opções fica melhor para fazermos o seu envio?_"
                )

                texto_editavel = st.text_area(
                    "Pré-visualização:",
                    value=mensagem_vendedor,
                    height=250,
                    key="txt_area_print",
                )
                link_whatsapp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_editavel)}"

                st.markdown(
                    f"""
                    <a href="{link_whatsapp}" target="_blank" style="text-decoration: none;">
                        <div style="background: linear-gradient(135deg, #25d366 0%, #16a34a 100%); color: white; text-align: center; padding: 16px; border-radius: 12px; font-weight: 700; margin-bottom: 8px;">
                            📲 ENVIAR COTAÇÃO PARA O WHATSAPP DO CLIENTE
                        </div>
                    </a>
                """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    "📋 COPIAR TEXTO DA COTAÇÃO", key="btn_pure_copy_frete"
                ):
                    texto_js_safe = (
                        texto_editavel.replace("\\", "\\\\")
                        .replace("`", "\\`")
                        .replace("$", "\\$")
                        .replace("\n", "\\n")
                    )
                    st.components.v1.html(
                        f"""
                        <script>
                        parent.navigator.clipboard.writeText(`{texto_js_safe}`);
                        alert("Cotação copiada com sucesso! 🎉");
                        </script>
                    """,
                        height=0,
                    )

                st.markdown("</div>", unsafe_allow_html=True)


# --- EXIBIÇÃO DA TELA: RASTREAMENTO DIRETO PARA CLIENTE OU USO INTERNO ---
elif st.session_state.tela_ativa == "rastreio" or rastreio_param:

    if rastreio_param:
        codigo_rastreio = rastreio_param
        transportadora_rastreio = transp_param

        txt_boas_vindas_cli = f"Olá, <b>{cliente_param}</b>! " if cliente_param else ""

        st.markdown(f"""
        <div class="bloco-etapa">
            <h3 style="color: #1e3a8a; margin-top: 0;">📦 {txt_boas_vindas_cli}Rastreamento Online</h3>
            <p style="color: #64748b; margin-bottom: 0;">Acompanhe o status da sua entrega com a <b>Cia do Jeans</b>.</p>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown('<div class="bloco-etapa">', unsafe_allow_html=True)
        st.markdown(
            '<div class="titulo-etapa">📦 PASSO ÚNICO: Gerar Rastreio para o Cliente</div>',
            unsafe_allow_html=True,
        )

        col_nome_cli, col_transp, col_cod, col_doc = st.columns([1.2, 1.2, 1.2, 1])

        with col_nome_cli:
            nome_cliente_rastreio = st.text_input(
                "Nome do Cliente:",
                placeholder="Ex: Maria Silva",
                key="campo_nome_cliente_estavel",
            ).strip()

        with col_transp:
            transportadora_rastreio = st.selectbox(
                "Selecione a Transportadora:",
                ["J&T Express", "Correios", "Braspress", "Azul Cargo", "Jadlog"],
                key="box_selecao_transportadora_estavel",
            )

        with col_cod:
            codigo_rastreio = st.text_input(
                "Código de Rastreio / Nº Nota Fiscal / AWB:",
                value="",
                placeholder="Ex: BR123456789X / 4552 / 51177221",
                key="campo_codigo_estavel",
            ).strip()

        with col_doc:
            doc_cliente = st.text_input(
                "CPF ou CNPJ do Cliente (Se J&T/Braspress/Jadlog):",
                placeholder="Apenas números",
                key="campo_doc_estavel",
            ).strip()

        btn_gerar_mensagem = st.button(
            "⚙️ GERAR INFORMAÇÕES DE RASTREAMENTO",
            type="primary",
            use_container_width=True,
            key="action_processar_rastreio",
            on_click=resetar_texto_rastreio,
        )

        if btn_gerar_mensagem:
            if not codigo_rastreio:
                st.error("⚠️ Por favor, digite o código de rastreio antes de gerar.")
                st.session_state["rastreio_gerado"] = False
            else:
                st.session_state["rastreio_gerado"] = True

    if (st.session_state.get("rastreio_gerado", False) and codigo_rastreio) or rastreio_param:

        if not rastreio_param:
            context = getattr(st, "context", None)
            if context and hasattr(context, "headers"):
                headers = context.headers
            elif isinstance(context, dict):
                headers = context.get("headers", {})
            else:
                headers = {}

            host_atual = headers.get("host", "")
            
            if host_atual:
                base_url = f"https://{host_atual}"
            else:
                base_url = "https://appteste-ciadojeans.streamlit.app"

            link_rastreio_personalizado = f"{base_url}/?rastreio={codigo_rastreio}&transp={urllib.parse.quote(transportadora_rastreio)}&cliente={urllib.parse.quote(nome_cliente_rastreio)}"

            txt_saudacao = f"Olá, *{nome_cliente_rastreio}*!" if nome_cliente_rastreio else "Olá!"
            
            mensagem_rastreio = (
                f"{txt_saudacao} Seu pedido da *Cia do Jeans* já foi despachado! 🎉\n\n"
                f"🚚 *Transportadora:* {transportadora_rastreio}\n"
                f"📦 *Código de Rastreio:* `{codigo_rastreio}`\n\n"
                "🔗 *Clique no link abaixo para acompanhar seu envio em tempo real:*\n"
                f"{link_rastreio_personalizado}"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            texto_rastreio_editavel = st.text_area(
                "Pré-visualização da Mensagem de Rastreio:",
                value=mensagem_rastreio,
                height=180,
                key="txt_area_rastreio",
            )
            texto_rastreio_codificado = urllib.parse.quote(texto_rastreio_editavel)
            link_whatsapp_rastreio = f"https://api.whatsapp.com/send?text={texto_rastreio_codificado}"

            st.markdown(
                f"""
                <a href="{link_whatsapp_rastreio}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #25d366 0%, #16a34a 100%); color: white; text-align: center; padding: 16px; border-radius: 12px; font-weight: 700; font-size: 16px; margin-bottom: 8px; font-family: sans-serif;">
                        📲 ENVIAR MENSAGEM DE RASTREIO PARA O WHATSAPP
                    </div>
                </a>
            """,
                unsafe_allow_html=True,
            )

            if st.button(
                "📋 COPIAR TEXTO DO RASTREIO", key="btn_pure_copy_rastreio"
            ):
                texto_rastreio_js_safe = (
                    texto_rastreio_editavel.replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                    .replace("\n", "\\n")
                )
                st.components.v1.html(
                    f"""
                    <script>
                    parent.navigator.clipboard.writeText(`{texto_rastreio_js_safe}`);
                    alert("Rastreio copiado com sucesso! 🎉");
                    </script>
                """,
                    height=0,
                )

            st.markdown("---")

        st.markdown(f"### 🚚 Transportado Por {transportadora_rastreio}")

        # TRATAMENTO ESPECIAL PARA J&T EXPRESS
        if "j&t" in transportadora_rastreio.lower() or "jandt" in transportadora_rastreio.lower():
            st.markdown(f"""
            <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <div style="font-size: 40px; margin-bottom: 10px;">📦</div>
                <h4 style="margin: 0 0 8px 0; color: #1e3a8a;">Rastreamento J&T Express</h4>
                <p style="color: #64748b; font-size: 14px; margin-bottom: 18px;">
                    O rastreamento da <b>J&T Express</b> é realizado diretamente no portal oficial com autenticação de segurança.
                </p>
                <div style="background-color: #f1f5f9; padding: 12px 20px; border-radius: 10px; display: inline-block; margin-bottom: 10px; border: 1px dashed #cbd5e1;">
                    <span style="font-size: 13px; color: #475569;">Código do Envio:</span> 
                    <strong style="font-size: 16px; color: #0f172a;">{codigo_rastreio}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
            with col_btn2:
                btn_copiar_jt = st.button("📋 COPIAR CÓDIGO DE RASTREIO", key="btn_copiar_jt_code", use_container_width=True)
                if btn_copiar_jt:
                    st.components.v1.html(
                        f"""
                        <script>
                        parent.navigator.clipboard.writeText("{codigo_rastreio}");
                        alert("Código de Rastreio {codigo_rastreio} copiado com sucesso! 🎉");
                        </script>
                        """,
                        height=0,
                    )
                    st.success(f"✅ Código {codigo_rastreio} copiado com sucesso!")

            st.markdown(f"""
            <div style="text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; margin-top: 15px;">
                <p style="color: #1e3a8a; font-weight: 600; font-size: 15px; margin-bottom: 12px;">
                    👇 Clique no botão abaixo para ir ao portal oficial da J&T Express e cole o código copiado:
                </p>
                <a href="https://www.jtexpress.com.br/trajectoryQuery?billCode={codigo_rastreio}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; display: inline-block; padding: 14px 28px; border-radius: 12px; font-weight: 700; font-size: 15px;">
                        🔗 ACOMPANHAR ENTREGA NA J&T EXPRESS
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

        # TRATAMENTO ESPECIAL PARA CORREIOS (PADRONIZADO EXATO IGUAL DA FOTO)
        elif "correio" in transportadora_rastreio.lower():
            cod_correios = codigo_rastreio.strip().upper()
            url_correios_site = f"https://rastreamento.correios.com.br/app/index.php?codigo={cod_correios}"

            status_correios = "Objeto Postado"
            tipo_entrega_correios = "PAC" if cod_correios.startswith("P") or cod_correios.startswith("O") or cod_correios.startswith("Q") else ("SEDEX" if cod_correios.startswith("S") or cod_correios.startswith("A") else "PAC / SEDEX")
            historico_correios = []

            with st.spinner(f"🔍 Buscando rastreio real para {cod_correios}..."):
                try:
                    url_api = f"https://api.linketrack.com/track/json?user=teste&token=1fe10a01fe10a01fe10a01fe10a0&codigo={cod_correios}"
                    res = requests.get(url_api, timeout=6)
                    if res.status_code == 200:
                        dados = res.json()
                        eventos = dados.get("eventos", [])
                        if eventos:
                            primeiro_ev = eventos[0]
                            st_nome = primeiro_ev.get("status", "")
                            st_local = primeiro_ev.get("local", "")
                            st_data = primeiro_ev.get("data", "")
                            st_hora = primeiro_ev.get("hora", "")
                            
                            sub_ev_str = ""
                            if primeiro_ev.get("subStatus"):
                                sub_ev_str = f" - {primeiro_ev.get('subStatus')[0]}"
                                
                            status_correios = f"{st_nome}{sub_ev_str} ({st_data} às {st_hora})"
                            
                            for ev in eventos:
                                d_ev = ev.get("data", "")
                                h_ev = ev.get("hora", "")
                                s_ev = ev.get("status", "")
                                l_ev = ev.get("local", "")
                                sub_txt = f" - {ev.get('subStatus')[0]}" if ev.get("subStatus") else ""
                                loc_txt = f" [{l_ev}]" if l_ev else ""
                                historico_correios.append(f"<b>{d_ev} {h_ev}</b>: {s_ev}{sub_txt}{loc_txt}")
                except Exception:
                    pass

                # Fallback via scraping caso a API não retorne eventos no momento
                if not historico_correios:
                    try:
                        resp_alt = requests.get(f"https://rastreadordeencomendas.com/result.php?idcod={cod_correios}", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                        if resp_alt.status_code == 200 and "<tr" in resp_alt.text:
                            linhas_tr = re.findall(r'<tr[^>]*>(.*?)</tr>', resp_alt.text, re.DOTALL)
                            for tr in linhas_tr:
                                colunas = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                                if len(colunas) >= 2:
                                    txt_data = re.sub(r'<[^>]+>', '', colunas[0]).strip()
                                    txt_desc = re.sub(r'<[^>]+>', '', colunas[1]).strip()
                                    if txt_data and txt_desc:
                                        historico_correios.append(f"<b>{txt_data}</b>: {txt_desc}")
                            if historico_correios:
                                status_correios = historico_correios[0].replace('<b>', '').replace('</b>', '')
                    except Exception:
                        pass

            if not historico_correios:
                historico_correios = [
                    f"<b>{cod_correios}:</b> Pedido registrado no sistema dos Correios.",
                    "<b>Status:</b> Acompanhe as movimentações completas no portal oficial."
                ]

            html_historico_correios = "".join([f'<li style="margin-bottom: 8px; color: #334155;">{h}</li>' for h in historico_correios])

            st.html(f"""
            <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 16px;">
                    <div>
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #2563eb; font-weight: 700;">STATUS DO ENVIO</span>
                        <h4 style="margin: 2px 0 0 0; color: #0f172a; font-size: 18px;">📦 Correios</h4>
                    </div>
                    <div style="background-color: #eff6ff; padding: 6px 14px; border-radius: 8px; border: 1px solid #dbeafe;">
                        <span style="font-size: 13px; color: #1e40af; font-weight: 600;">COD: {cod_correios}</span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 20px;">
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Status Atual</span>
                        <strong style="font-size: 14px; color: #1e3a8a;">{status_correios}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Tipo de Entrega</span>
                        <strong style="font-size: 15px; color: #0f172a;">{tipo_entrega_correios}</strong>
                    </div>
                </div>

                <div style="background: #f1f5f9; padding: 16px; border-radius: 12px; border-left: 4px solid #2563eb;">
                    <strong style="font-size: 14px; color: #0f172a; display: block; margin-bottom: 10px;">📍 Histórico de Movimentações:</strong>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        {html_historico_correios}
                    </ul>
                </div>
            </div>
            """)

            st.markdown(f"""
            <div style="text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; margin-top: 15px;">
                <p style="color: #1e3a8a; font-weight: 600; font-size: 15px; margin-bottom: 12px;">
                    👇 Clique no botão abaixo para conferir a movimentação no portal dos Correios:
                </p>
                <a href="{url_correios_site}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; display: inline-block; padding: 16px 32px; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        🔗 CONSULTAR COMPLETO NO PORTAL CORREIOS
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

        # TRATAMENTO ESPECIAL PARA JADLOG (PADRONIZADO EXATO IGUAL DA FOTO)
        elif "jadlog" in transportadora_rastreio.lower():
            cod_jadlog = codigo_rastreio.strip()
            doc_limpo = "".join(filter(str.isdigit, st.session_state.get("campo_doc_estavel", "")))
            
            url_jadlog_site = f"https://www.jadlog.com.br/jadlog/tracking?cte={cod_jadlog}"
            status_jadlog = "Em Trânsito"
            tipo_entrega_jadlog = "Jadlog Package"
            historico_jadlog = []

            with st.spinner(f"🔍 Buscando rastreio real na Jadlog para {cod_jadlog}..."):
                try:
                    url_api_j = "https://www.jadlog.com.br/jadlog/shipment/tracking"
                    payload_j = {"cte": cod_jadlog, "cnpj": doc_limpo if doc_limpo else ""}
                    headers_j = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
                    
                    res_j = requests.post(url_api_j, json=payload_j, headers=headers_j, timeout=6)
                    if res_j.status_code == 200:
                        dados_j = res_j.json()
                        eventos_j = dados_j.get("tracking", {}).get("eventos", [])
                        servico_j = dados_j.get("tracking", {}).get("modalidade", "")

                        if servico_j:
                            tipo_entrega_jadlog = f"Jadlog {servico_j.upper()}"

                        if eventos_j:
                            primeiro_ev = eventos_j[0]
                            dt_j = primeiro_ev.get("data", "")
                            st_j = primeiro_ev.get("status", "")
                            un_j = primeiro_ev.get("unidade", "")
                            txt_un_j = f" - {un_j}" if un_j else ""
                            status_jadlog = f"{st_j}{txt_un_j} ({dt_j})"

                            for ev in eventos_j:
                                data_e = ev.get("data", "")
                                st_e = ev.get("status", "")
                                un_e = ev.get("unidade", "")
                                txt_un = f" [{un_e}]" if un_e else ""
                                historico_jadlog.append(f"<b>{data_e}</b>: {st_e}{txt_un}")
                except Exception:
                    pass

                # Fallback de busca caso a API passe por instabilidade
                if not historico_jadlog:
                    try:
                        resp_alt = requests.get(f"https://rastreadordeencomendas.com/result.php?idcod={cod_jadlog}", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                        if resp_alt.status_code == 200 and "<tr" in resp_alt.text:
                            linhas_tr = re.findall(r'<tr[^>]*>(.*?)</tr>', resp_alt.text, re.DOTALL)
                            for tr in linhas_tr:
                                colunas = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                                if len(colunas) >= 2:
                                    txt_data = re.sub(r'<[^>]+>', '', colunas[0]).strip()
                                    txt_desc = re.sub(r'<[^>]+>', '', colunas[1]).strip()
                                    if txt_data and txt_desc:
                                        historico_jadlog.append(f"<b>{txt_data}</b>: {txt_desc}")
                            if historico_jadlog:
                                status_jadlog = historico_jadlog[0].replace('<b>', '').replace('</b>', '')
                    except Exception:
                        pass

            if not historico_jadlog:
                historico_jadlog = [
                    f"<b>{cod_jadlog}:</b> Encomenda registrada na base de dados da Jadlog.",
                    "<b>Status:</b> Acompanhe as movimentações no portal oficial da transportadora."
                ]

            html_historico_jadlog = "".join([f'<li style="margin-bottom: 8px; color: #334155;">{h}</li>' for h in historico_jadlog])

            st.html(f"""
            <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 16px;">
                    <div>
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #2563eb; font-weight: 700;">STATUS DO ENVIO</span>
                        <h4 style="margin: 2px 0 0 0; color: #0f172a; font-size: 18px;">🚚 Jadlog Logística</h4>
                    </div>
                    <div style="background-color: #eff6ff; padding: 6px 14px; border-radius: 8px; border: 1px solid #dbeafe;">
                        <span style="font-size: 13px; color: #1e40af; font-weight: 600;">REM/CPF: {cod_jadlog}</span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 20px;">
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Status Atual</span>
                        <strong style="font-size: 14px; color: #1e3a8a;">{status_jadlog}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Tipo de Entrega</span>
                        <strong style="font-size: 15px; color: #0f172a;">{tipo_entrega_jadlog}</strong>
                    </div>
                </div>

                <div style="background: #f1f5f9; padding: 16px; border-radius: 12px; border-left: 4px solid #2563eb;">
                    <strong style="font-size: 14px; color: #0f172a; display: block; margin-bottom: 10px;">📍 Histórico de Movimentações:</strong>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        {html_historico_jadlog}
                    </ul>
                </div>
            </div>
            """)

            st.markdown(f"""
            <div style="text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; margin-top: 15px;">
                <p style="color: #1e3a8a; font-weight: 600; font-size: 15px; margin-bottom: 12px;">
                    👇 Clique no botão abaixo para conferir a movimentação no portal da Jadlog:
                </p>
                <a href="{url_jadlog_site}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; display: inline-block; padding: 16px 32px; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        🔗 CONSULTAR COMPLETO NO PORTAL JADLOG
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

        # TRATAMENTO ESPECIAL PARA AZUL CARGO (SEM ERROS DE SINTAXE E COM CONSULTA RÁPIDA)
        elif "azul" in transportadora_rastreio.lower():
            digitos_apenas = "".join(filter(str.isdigit, codigo_rastreio))
            
            if len(digitos_apenas) >= 8:
                awb_codigo = digitos_apenas[-8:]
            else:
                awb_codigo = digitos_apenas if digitos_apenas else codigo_rastreio

            url_azul_site = f"https://www.azullogistica.com.br/Rastreio/Rastrear?awb={awb_codigo}"
            url_api_hub = f"https://api.linketrack.com/track/json?user=teste&token=1fe10a01fe10a01fe10a01fe10a0&codigo={awb_codigo}"

            status_azul = None
            previsao_azul = "Acompanhar no Portal"
            tipo_entrega_azul = "Aéreo / Expresso"
            origem_destino_azul = "Goiânia (GYN) ➔ Destino"
            historico_azul = []

            with st.spinner(f"🔍 Consultando AWB {awb_codigo} na Azul Cargo Express..."):
                try:
                    res = requests.get(url_api_hub, timeout=5)
                    if res.status_code == 200:
                        dados = res.json()
                        eventos = dados.get("eventos", [])
                        if eventos:
                            status_azul = eventos[0].get("status")
                            for ev in eventos:
                                data_ev = ev.get("data", "")
                                hora_ev = ev.get("hora", "")
                                st_ev = ev.get("status", "")
                                sub_ev = ev.get("subStatus", [])
                                txt_sub = f" ({sub_ev[0]})" if sub_ev else ""
                                historico_azul.append(f"<b>{data_ev} {hora_ev}</b> - {st_ev}{txt_sub}")
                except Exception:
                    pass

            if not status_azul:
                status_azul = "Em Trânsito / Processamento"
            
            if not historico_azul:
                historico_azul = [
                    f"<b>AWB {awb_codigo}:</b> Encomenda registrada na base de dados da Azul Cargo Express.",
                    "<b>Acompanhamento:</b> Para visualizar todos os detalhes do voo e etapas de entrega, clique no botão abaixo."
                ]

            html_historico_azul = "".join([f'<li style="margin-bottom: 8px; color: #334155;">{h}</li>' for h in historico_azul])
            cor_status = "#16a34a" if "entreg" in status_azul.lower() else "#1e3a8a"

            st.html(f"""
            <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 16px;">
                    <div>
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #2563eb; font-weight: 700;">STATUS DO ENVIO</span>
                        <h4 style="margin: 2px 0 0 0; color: #0f172a; font-size: 18px;">✈️ Azul Cargo Express</h4>
                    </div>
                    <div style="background-color: #eff6ff; padding: 6px 14px; border-radius: 8px; border: 1px solid #dbeafe;">
                        <span style="font-size: 13px; color: #1e40af; font-weight: 600;">AWB: {awb_codigo}</span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Status Atual</span>
                        <strong style="font-size: 15px; color: {cor_status};">{status_azul}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Previsão de Entrega</span>
                        <strong style="font-size: 15px; color: #0f172a;">{previsao_azul}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Modalidade</span>
                        <strong style="font-size: 15px; color: #0f172a;">{tipo_entrega_azul}</strong>
                    </div>
                </div>

                <div style="background: #f8fafc; padding: 12px 14px; border-radius: 10px; border: 1px solid #f1f5f9; margin-bottom: 16px;">
                    <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 2px;">Origem ➔ Destino</span>
                    <strong style="font-size: 14px; color: #1e3a8a;">{origem_destino_azul}</strong>
                </div>

                <div style="background: #f1f5f9; padding: 16px; border-radius: 12px; border-left: 4px solid #2563eb;">
                    <strong style="font-size: 14px; color: #0f172a; display: block; margin-bottom: 10px;">📍 Histórico de Movimentações:</strong>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        {html_historico_azul}
                    </ul>
                </div>
            </div>
            """)

            st.markdown(f"""
            <div style="text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; margin-top: 15px;">
                <p style="color: #1e3a8a; font-weight: 600; font-size: 15px; margin-bottom: 12px;">
                    👇 Clique abaixo para conferir a movimentação direta no portal da Azul:
                </p>
                <a href="{url_azul_site}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; display: inline-block; padding: 16px 32px; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        🔗 CONSULTAR NO PORTAL AZUL LOGÍSTICA
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

        # TRATAMENTO ESPECIAL PARA BRASPRESS (PARSER AJUSTADO PARA CAPTURAR DATA, HORA E DESCRIÇÃO)
        elif "braspress" in transportadora_rastreio.lower():
            cod_braspress = "".join(filter(str.isdigit, codigo_rastreio))
            if not cod_braspress:
                cod_braspress = codigo_rastreio

            doc_limpo = "".join(filter(str.isdigit, st.session_state.get("campo_doc_estavel", "")))
            cnpj_utilizado = doc_limpo if doc_limpo else "34835571000168"

            url_braspress_tracking = f"https://blue.braspress.com/site/w/tracking/search?cnpj={cnpj_utilizado}&documentType=NOTAFISCAL&numero={cod_braspress}"

            headers_braspress = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }

            previsao_ext = "-"
            status_ext = "Em viagem para Destino (Braspress)"
            tipo_entrega_ext = "Padrão"
            historico_ocorrencias = []

            with st.spinner("🔍 Buscando dados em tempo real no servidor da Braspress..."):
                try:
                    res_bp = requests.get(url_braspress_tracking, headers=headers_braspress, timeout=6)
                    if res_bp.status_code == 200:
                        html_text = res_bp.text
                        
                        match_status = re.search(r"Status\s*</th>\s*<td[^>]*>(.*?)</td>", html_text, re.IGNORECASE | re.DOTALL)
                        if match_status:
                            status_limpo = re.sub(r'<[^>]+>', '', match_status.group(1)).strip()
                            if status_limpo:
                                status_ext = status_limpo

                        match_prev = re.search(r"Previsão de Entrega\s*</th>\s*<td[^>]*>(\d{2}/\d{2}/\d{4})</td>", html_text, re.IGNORECASE)
                        if match_prev:
                            previsao_ext = match_prev.group(1)

                        # Mapeamento de todas as linhas de tabela no HTML da Braspress
                        linhas_tr = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.DOTALL | re.IGNORECASE)
                        for tr in linhas_tr:
                            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL | re.IGNORECASE)
                            if len(tds) >= 2:
                                # Limpeza de cada célula descartando tags HTML extras
                                cols_limpas = [re.sub(r'<[^>]+>', ' ', td).strip() for td in tds]
                                cols_limpas = [re.sub(r'\s+', ' ', c) for c in cols_limpas if c]
                                
                                if cols_limpas:
                                    primeira_col = cols_limpas[0]
                                    # Verifica se a primeira coluna possui formato de Data/Hora
                                    if re.search(r'\d{2}/\d{2}/\d{4}', primeira_col):
                                        detalhes_evento = " - ".join(cols_limpas[1:]) if len(cols_limpas) > 1 else status_ext
                                        historico_ocorrencias.append(f"<b>{primeira_col}</b> - {detalhes_evento}")

                except Exception:
                    pass

                # Fallback secundário para raspar caso a tabela principal não estivesse visível
                if not historico_ocorrencias:
                    try:
                        resp_alt = requests.get(f"https://rastreadordeencomendas.com/result.php?idcod={cod_braspress}", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                        if resp_alt.status_code == 200 and "<tr" in resp_alt.text:
                            linhas_tr = re.findall(r'<tr[^>]*>(.*?)</tr>', resp_alt.text, re.DOTALL)
                            for tr in linhas_tr:
                                colunas = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                                if len(colunas) >= 2:
                                    txt_data = re.sub(r'<[^>]+>', '', colunas[0]).strip()
                                    txt_desc = re.sub(r'<[^>]+>', '', colunas[1]).strip()
                                    if txt_data and txt_desc:
                                        historico_ocorrencias.append(f"<b>{txt_data}</b> - {txt_desc}")
                    except Exception:
                        pass

            if not historico_ocorrencias:
                historico_ocorrencias = [
                    f"<b>NF {cod_braspress}:</b> Pedido registrado no sistema da Braspress.",
                    f"<b>Status Atual:</b> {status_ext}. Acompanhe as movimentações no portal oficial da transportadora."
                ]

            html_historico = "".join([f'<li style="margin-bottom: 8px; color: #334155;">{h}</li>' for h in historico_ocorrencias])

            st.html(f"""
            <div style="background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 16px;">
                    <div>
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #2563eb; font-weight: 700;">STATUS DO ENVIO</span>
                        <h4 style="margin: 2px 0 0 0; color: #0f172a; font-size: 18px;">🚚 Braspress Transportes</h4>
                    </div>
                    <div style="background-color: #eff6ff; padding: 6px 14px; border-radius: 8px; border: 1px solid #dbeafe;">
                        <span style="font-size: 13px; color: #1e40af; font-weight: 600;">NF: {cod_braspress}</span>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Status Atual</span>
                        <strong style="font-size: 15px; color: #1e3a8a;">{status_ext}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Previsão de Entrega</span>
                        <strong style="font-size: 15px; color: #0f172a;">{previsao_ext}</strong>
                    </div>
                    <div style="background: #f8fafc; padding: 14px; border-radius: 10px; border: 1px solid #f1f5f9;">
                        <span style="font-size: 12px; color: #64748b; display: block; margin-bottom: 4px;">Tipo de Entrega</span>
                        <strong style="font-size: 15px; color: #0f172a;">{tipo_entrega_ext}</strong>
                    </div>
                </div>

                <div style="background: #f1f5f9; padding: 16px; border-radius: 12px; border-left: 4px solid #2563eb;">
                    <strong style="font-size: 14px; color: #0f172a; display: block; margin-bottom: 10px;">📍 Histórico de Movimentações:</strong>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        {html_historico}
                    </ul>
                </div>
            </div>
            """)

            st.markdown(f"""
            <div style="text-align: center; font-family: 'Plus Jakarta Sans', sans-serif; margin-top: 15px;">
                <p style="color: #1e3a8a; font-weight: 600; font-size: 15px; margin-bottom: 12px;">
                    👇 Clique no botão abaixo para conferir a movimentação no portal da Braspress:
                </p>
                <a href="{url_braspress_tracking}" target="_blank" style="text-decoration: none;">
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; display: inline-block; padding: 16px 32px; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                        🔗 CONSULTAR COMPLETO NO PORTAL BRASPRESS
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

        else:
            with st.spinner(f"🔍 Buscando dados de rastreamento na {transportadora_rastreio}..."):
                try:
                    url_consulta = f"https://rastreadordeencomendas.com/result.php?idcod={codigo_rastreio}"
                    resp = requests.get(url_consulta, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    
                    if resp.status_code == 200 and "<table" in resp.text:
                        inicio_tab = resp.text.find("<table")
                        fim_tab = resp.text.find("</table>") + 8
                        tabela_html = resp.text[inicio_tab:fim_tab]

                        st.html(f"""
                        <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif;">
                            <h4 style="margin-top: 0; color: #1e3a8a;">📦 Status da Encomenda: {codigo_rastreio}</h4>
                            <style>
                                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                                th, td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 14px; }}
                                td strong {{ color: #0f172a; display: block; margin-bottom: 2px; }}
                                td p {{ margin: 2px 0; color: #475569; font-size: 13px; }}
                            </style>
                            {tabela_html}
                        </div>
                        """)
                    else:
                        st.info(f"ℹ️ O pedido **{codigo_rastreio}** deu entrada na **{transportadora_rastreio}** e as atualizações do sistema estarão disponíveis em breve.")
                except Exception as err:
                    st.error(f"⚠️ Não foi possível carregar as informações no momento. Tente novamente mais tarde.")

    st.markdown("</div>", unsafe_allow_html=True)
