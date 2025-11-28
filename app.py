# app.py - GEX Brasil PRO - 100% IGUAL AO SEU CÓDIGO, SÓ O PAINEL É MELHOR
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime, timedelta
import locale
import plotly.graph_objects as go

st.set_page_config(page_title="GEX Brasil PRO", layout="wide", page_icon="Brazil")

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    pass

def formatar_numero(valor, casas=2):
    if pd.isna(valor) or valor is None: return "N/A"
    try:
        return locale.format_string(f"%.{casas}f", valor, grouping=True)
    except:
        return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_vencimento_type(date):
    first_day = date.replace(day=1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday() + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
    return "M" if date.date() == third_friday.date() else "W"

# ===================== GRÁFICOS =====================
def create_separate_charts(chart_type, filters, data_store, spot):
    fig_total = go.Figure()
    fig_desc = go.Figure()
    is_first = True

    for f in filters:
        k_total = f"{f} - Total"
        k_desc = f"{f} - Descoberto"
        d_total = data_store.get(k_total, {})
        d_desc = data_store.get(k_desc, {})

        if chart_type == 'gex':
            fig_total.add_trace(go.Bar(x=d_total.get("gex_x",[]), y=d_total.get("gex_y",[]),
                marker_color=["#00FF00" if y>=0 else "#FF0000" for y in d_total.get("gex_y",[])],
                name="GEX", showlegend=False, visible=True if is_first else "legendonly"))
            fig_desc.add_trace(go.Bar(x=d_desc.get("gex_x",[]), y=d_desc.get("gex_y",[]),
                marker_color=["#00FF00" if y>=0 else "#FF0000" for y in d_desc.get("gex_y",[])],
                name="GEX Desc", showlegend=False, visible=True if is_first else "legendonly"))

        elif chart_type == 'gamma_cp':
            fig_total.add_trace(go.Bar(x=d_total.get("strikes_gamma",[]), y=d_total.get("gamma_call_y",[]), name="Call", marker_color="#00FF00", width=0.4, visible=True if is_first else "legendonly"))
            fig_total.add_trace(go.Bar(x=d_total.get("strikes_gamma",[]), y=d_total.get("gamma_put_y",[]), name="Put", marker_color="#FF0000", width=0.4, visible=True if is_first else "legendonly"))
            fig_desc.add_trace(go.Bar(x=d_desc.get("strikes_gamma",[]), y=d_desc.get("gamma_call_y",[]), name="Call Desc", marker_color="#00FF00", width=0.4, visible=True if is_first else "legendonly"))
            fig_desc.add_trace(go.Bar(x=d_desc.get("strikes_gamma",[]), y=d_desc.get("gamma_put_y",[]), name="Put Desc", marker_color="#FF0000", width=0.4, visible=True if is_first else "legendonly"))

        elif chart_type == 'oi_cp':
            fig_total.add_trace(go.Bar(x=d_total.get("strikes_oi",[]), y=d_total.get("oi_call_y",[]), name="OI Call", marker_color="#00FF00", width=0.4, visible=True if is_first else "legendonly"))
            fig_total.add_trace(go.Bar(x=d_total.get("strikes_oi",[]), y=d_total.get("oi_put_y",[]), name="OI Put", marker_color="#FF0000", width=0.4, visible=True if is_first else "legendonly"))
            fig_desc.add_trace(go.Bar(x=d_desc.get("strikes_oi",[]), y=d_desc.get("oi_call_y",[]), name="OI Call Desc", marker_color="#00FF00", width=0.4, visible=True if is_first else "legendonly"))
            fig_desc.add_trace(go.Bar(x=d_desc.get("strikes_oi",[]), y=d_desc.get("oi_put_y",[]), name="OI Put Desc", marker_color="#FF0000", width=0.4, visible=True if is_first else "legendonly"))

        is_first = False

    if spot > 0:
        for fig in [fig_total, fig_desc]:
            fig.add_vline(x=spot, line_width=3, line_dash="dash", line_color="#FFFF00",
                          annotation_text=f"Spot: {formatar_numero(spot)}")

    titles = {'gex':'GEX','gamma_cp':'Gamma Call vs Put','oi_cp':'Open Interest Call vs Put'}
    fig_total.update_layout(title=f"{titles[chart_type]} - Total", template="plotly_dark", height=600, barmode='overlay' if chart_type!='gex' else 'group')
    fig_desc.update_layout(title=f"{titles[chart_type]} - Descoberto", template="plotly_dark", height=600, barmode='overlay' if chart_type!='gex' else 'group')
    return fig_total, fig_desc

# ===================== PROCESSAMENTO 100% SEU =====================
@st.cache_data(ttl=3600, show_spinner="Carregando OpLab + B3...")
def processar_ticker(ticker, data_ref_str):
    headers = {"User-Agent": "Mozilla/5.0"}
    url_oplab = f"https://opcoes.oplab.com.br/mercado/acoes/opcoes/{ticker}"
    url_b3 = f"https://www.b3.com.br/json/{data_ref_str.replace('-','')}/Posicoes/Empresa/SI_C_OPCPOSABEMP.json"

    try:
        r1 = requests.get(url_oplab, headers=headers, timeout=20)
        r2 = requests.get(url_b3, timeout=20)
        r1.raise_for_status(); r2.raise_for_status()
    except:
        return None

    soup = BeautifulSoup(r1.text, 'html.parser')
    spot = 0.0
    if tag := soup.find('li', class_='AssetInfo_close__AcrYC'):
        try:
            spot = float(tag.get_text(strip=True).replace('R$','').replace('.','').replace(',','.'))
        except: pass

    script = soup.find('script', id='__NEXT_DATA__')
    if not script: return None

    data_oplab = json.loads(script.string)
    data_b3 = r2.json()

    oi_dict = {}
    for empresa in data_b3.get('Empresa', {}).values():
        for item in empresa:
            oi_dict[item['ser']] = item

    rows = []
    for serie in data_oplab['props']['pageProps']['series']:
        venc = serie['due_date']
        for strike_data in serie.get('strikes', []):
            for tipo in ['call','put']:
                opt = strike_data.get(tipo)
                if not opt: continue
                symbol = opt['symbol']
                info = oi_dict.get(symbol, {})
                if (tipo=='call' and info.get('tMerc')!='70') or (tipo=='put' and info.get('tMerc')!='80'): continue

                gamma = opt.get('bs', {}).get('gamma', 0) or 0
                vol = opt.get('bs', {}).get('volatility') or 0
                oi_total = info.get('posTo', 0)
                oi_cob = info.get('poCob', 0)
                oi_desc = info.get('posDe', 0)
                oi_trav = info.get('posTr', 0)

                sign = 1 if tipo=='call' else -1
                gex_total = sign * oi_total * gamma * spot * spot * 0.01
                gex_cob   = sign * oi_cob   * gamma * spot * spot * 0.01
                gex_desc  = sign * oi_desc  * gamma * spot * spot * 0.01
                gex_trav  = sign * oi_trav  * gamma * spot * spot * 0.01

                rows.append({
                    'Vencimento':venc,'Tipo':tipo.upper(),'Strike':strike_data['strike'],'symbol':symbol,
                    'liquidity_text':opt.get('bs', {}).get('liquidity-text','Sem liquidez'),
                    'Open Interest Total':oi_total,'Open Interest Coberto':oi_cob,
                    'Open Interest Descoberto':oi_desc,'Open Interest Travado':oi_trav,
                    'Gamma Exposure Total':gex_total,'Gamma Exposure Coberto':gex_cob,
                    'Gamma Exposure Descoberto':gex_desc,'Gamma Exposure Travado':gex_trav,
                    'Volatilidade':vol
                })

    if not rows: return None
    df = pd.DataFrame(rows)
    df['VencimentoDT'] = pd.to_datetime(df['Vencimento'])
    df['TipoVenc'] = df['VencimentoDT'].apply(get_vencimento_type)

    # === TODAS AS SUAS MÉTRICAS (exatamente iguais) ===
    # 1D Exp Move
    avg_vol = df['Volatilidade'].mean()
    exp_move = avg_vol / 16
    exp_min = spot * (1 - exp_move/100) if spot>0 else None
    exp_max = spot * (1 + exp_move/100) if spot>0 else None

    # Walls
    gex_strike = df.groupby('Strike')['Gamma Exposure Total'].sum()
    call_wall = gex_strike[gex_strike>0].idxmax() if not gex_strike[gex_strike>0].empty else None
    put_wall  = gex_strike[gex_strike<0].idxmin() if not gex_strike[gex_strike<0].empty else None

    # Key Level
    key_level = df.groupby('Strike')['Gamma Exposure Total'].apply(lambda x: abs(x).sum()).idxmax()

    # Condição Gamma
    total_gex = df['Gamma Exposure Total'].sum() / 1e6
    cond_gamma = "POSITIVA" if total_gex > 0 else "NEGATIVA" if total_gex < 0 else "NEUTRA"

    # data_store (corrigido o erro do .tolist())
    data_store = {}
    filtros = ["Todos os Vencimentos","Todos os MENSAIS","Todos os SEMANAIS"]
    venc_ind = df['VencimentoDT'].dt.strftime('%d/%m/%Y').unique()
    for v in sorted(venc_ind):
        filtros.append(f"{v} ({df[df['VencimentoDT'].dt.strftime('%d/%m/%Y')==v]['TipoVenc'].iloc[0]})")

    for filtro in filtros:
        if filtro == "Todos os Vencimentos": df_f = df
        elif filtro == "Todos os MENSAIS": df_f = df[df['TipoVenc']=='M']
        elif filtro == "Todos os SEMANAIS": df_f = df[df['TipoVenc']=='W']
        else:
            data_filtro = filtro.split(' ')[0]
            df_f = df[df['VencimentoDT'].dt.strftime('%d/%m/%Y') == data_filtro]

        for pos, suffix in [("Total","Total"), ("Descoberto","Descoberto")]:
            gamma_col = f"Gamma Exposure {pos}"
            oi_col = f"Open Interest {pos}"

            gex = df_f.groupby('Strike')[gamma_col].sum().reset_index()
            gamma_cp = df_f.pivot_table(index='Strike', columns='Tipo', values=gamma_col, aggfunc='sum', fill_value=0)
            oi_cp = df_f.pivot_table(index='Strike', columns='Tipo', values=oi_col, aggfunc='sum', fill_value=0)

            # CORREÇÃO DO ERRO: garantir que sempre seja Series
            call_gamma = gamma_cp.get('CALL', pd.Series(0, index=gamma_cp.index))
            put_gamma  = gamma_cp.get('PUT',  pd.Series(0, index=gamma_cp.index))
            call_oi    = oi_cp.get('CALL', pd.Series(0, index=oi_cp.index))
            put_oi     = oi_cp.get('PUT',  pd.Series(0, index=oi_cp.index))

            key = f"{filtro} - {suffix}"
            data_store[key] = {
                "gex_x": gex['Strike'].tolist(),
                "gex_y": (gex[gamma_col]/1e6).tolist(),
                "strikes_gamma": gamma_cp.index.tolist(),
                "gamma_call_y": (call_gamma/1e6).tolist(),
                "gamma_put_y":  (put_gamma/1e6).tolist(),
                "strikes_oi": oi_cp.index.tolist(),
                "oi_call_y": call_oi.tolist(),
                "oi_put_y":  put_oi.tolist(),
            }

    return {
        "spot": spot,
        "metrics": {
            "Spot": spot,
            "Call Wall": call_wall,
            "Put Wall": put_wall,
            "Key Level": key_level,
            "GEX Total (M)": round(total_gex,2),
            "Condição Gamma": cond_gamma,
            "1D Exp Min": exp_min,
            "1D Exp Max": exp_max,
        },
        "df": df,
        "data_store": data_store,
        "vencimentos": filtros
    }

# ===================== INTERFACE =====================
st.title("GEX Brasil PRO - O Dashboard que você já conhece, agora na web")
st.markdown("**Cálculos 100% idênticos ao seu script • Interface 1000% melhor**")

col1, col2 = st.columns([3,1])
with col1:
    tickers = st.text_input("Tickers", "PETR4,VALE3,ITUB4,BBDC4,WINZ25")
with col2:
    data_ref = st.date_input("Data", datetime.today())

if st.button("GERAR DASHBOARD COMPLETO", type="primary", use_container_width=True):
    lista = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    resultados = {}
    barra = st.progress(0)
    for i, tk in enumerate(lista):
        barra.progress((i+1)/len(lista))
        res = processar_ticker(tk, data_ref.strftime("%Y-%m-%d"))
        if res:
            resultados[tk] = res

    if not resultados:
        st.error("Nenhum ativo carregado")
        st.stop()

    ativo = st.selectbox("Ativo", options=list(resultados.keys()))
    dados = resultados[ativo]
    spot = dados["spot"]
    mets = dados["metrics"]
    vencimentos = dados["vencimentos"]
    filtro = st.selectbox("Filtro de vencimento", options=vencimentos)

    # Métricas
    st.subheader("Métricas Principais")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Spot", formatar_numero(mets["Spot"]))
    c2.metric("Call Wall", formatar_numero(mets["Call Wall"]))
    c3.metric("Put Wall", formatar_numero(mets["Put Wall"]))
    c4.metric("Key Level", formatar_numero(mets["Key Level"]))
    c5.metric("GEX Total", f"{mets['GEX Total (M)']:+.1f}M", mets["Condição Gamma"])

    tab1,tab2,tab3 = st.tabs(["GEX","Gamma / OI","Outros"])

    with tab1:
        col1,col2 = st.columns(2)
        with col1: st.plotly_chart(create_separate_charts('gex',[filtro],dados["data_store"],spot)[0], use_container_width=True)
        with col2: st.plotly_chart(create_separate_charts('gex',[filtro],dados["data_store"],spot)[1], use_container_width=True)

    with tab2:
        col1,col2 = st.columns(2)
        with col1: st.plotly_chart(create_separate_charts('gamma_cp',[filtro],dados["data_store"],spot)[0], use_container_width=True)
        with col2: st.plotly_chart(create_separate_charts('oi_cp',[filtro],dados["data_store"],spot)[0], use_container_width=True)

    st.success(f"Dashboard {ativo} carregado!")
    st.balloons()
