# app.py - Dashboard Opções B3 + OpLab (GEX, Gamma, Walls, Skew) - Versão FINAL 2025
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import locale
import plotly.graph_objects as go
import time

st.set_page_config(page_title="GEX Brasil", layout="wide", page_icon="🇧🇷")

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    pass

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_dados_oplab(ticker, data_ref):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    url_oplab = f"https://opcoes.oplab.com.br/mercado/acoes/opcoes/{ticker}"
    url_b3 = f"https://www.b3.com.br/json/{data_ref}/Posicoes/Empresa/SI_C_OPCPOSABEMP.json"
    
    try:
        r1 = requests.get(url_oplab, headers=headers, timeout=15)
        r2 = requests.get(url_b3, timeout=15)
        r1.raise_for_status()
        r2.raise_for_status()
    except:
        return None

    soup = BeautifulSoup(r1.text, 'html.parser')
    spot = 0
    try:
        spot_tag = soup.find('li', class_='AssetInfo_close__AcrYC')
        if spot_tag:
            spot = float(spot_tag.text.replace('R$', '').replace('.', '').replace(',', '.').strip())
    except: spot = 0

    script = soup.find('script', id='__NEXT_DATA__')
    if not script: return None

    data_oplab = json.loads(script.string)
    data_b3 = r2.json()

    oi_dict = {}
    for itens in data_b3.get('Empresa', {}).values():
        for item in itens:
            oi_dict[item['ser']] = item

    options = []
    for serie in data_oplab['props']['pageProps']['series']:
        venc = serie['due_date']
        for strike in serie['strikes']:
            for tipo in ['call', 'put']:
                opt = strike.get(tipo)
                if not opt: continue
                
                symbol = opt['symbol']
                info = oi_dict.get(symbol, {})
                if (tipo == 'call' and info.get('tMerc') != '70') or (tipo == 'put' and info.get('tMerc') != '80'):
                    continue

                gamma = opt.get('bs', {}).get('gamma', 0) or 0
                vol = opt.get('bs', {}).get('volatility') or 0
                oi_total = info.get('posTo', 0)
                oi_desc = info.get('posDe', 0)

                sign = 1 if tipo == 'call' else -1
                gex_total = sign * oi_total * gamma * spot * spot * 0.01
                gex_desc = sign * oi_desc * gamma * spot * spot * 0.01

                options.append({
                    'venc': venc,
                    'tipo': tipo.upper(),
                    'strike': strike['strike'],
                    'symbol': symbol,
                    'oi_total': oi_total,
                    'oi_desc': oi_desc,
                    'gex_total': gex_total,
                    'gex_desc': gex_desc,
                    'vol': vol,
                    'liquidez': opt.get('bs', {}).get('liquidity-text', 'Baixa')
                })

    return pd.DataFrame(options), spot

def formatar(v):
    if pd.isna(v) or v is None: return "N/A"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===================== INTERFACE =====================
st.title("🇧🇷 GEX Brasil - O Melhor Dashboard de Opções da B3")
st.markdown("**Gamma Exposure, Call/Put Walls, Key Levels, Skew e muito mais — 100% grátis**")

col1, col2 = st.columns([3,1])
with col1:
    tickers = st.text_input("Tickers (separados por vírgula)", "PETR4, VALE3, ITUB4, BBDC4, WINZ25")
with col2:
    data_ref = st.date_input("Data", datetime.today())

tickers_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

if st.button("🚀 GERAR DASHBOARD COMPLETO", type="primary", use_container_width=True):
    progress = st.progress(0)
    resultados = {}

    for i, ticker in enumerate(tickers_list):
        progress.progress((i+1)/len(tickers_list))
        with st.spinner(f"Processando {ticker}..."):
            dados = buscar_dados_oplab(ticker, data_ref.strftime("%Y%m%d"))
            if dados:
                df, spot = dados
                if not df.empty:
                    resultados[ticker] = (df, spot)

    if not resultados:
        st.error("Nenhum ativo carregou. Verifique os tickers ou conexão.")
        st.stop()

    ticker = st.selectbox("Selecione o ativo", options=list(resultados.keys()))
    df, spot = resultados[ticker]

    # Métricas principais
    gex_total = df['gex_total'].sum() / 1e6
    condicao = "POSITIVA 🔥" if gex_total > 0 else "NEGATIVA ❄️" if gex_total < 0 else "NEUTRA"

    call_wall = df[df['gex_total'] > 0].groupby('strike')['gex_total'].sum().idxmax() if not df[df['gex_total'] > 0].empty else None
    put_wall = df[df['gex_total'] < 0].groupby('strike')['gex_total'].sum().idxmin() if not df[df['gex_total'] < 0].empty else None
    key_level = df.groupby('strike')['gex_total'].apply(lambda x: abs(x).sum()).idxmax()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Spot Price", f"R$ {formatar(spot)}")
    col2.metric("GEX Total", f"{gex_total:+.2f}M", condicao)
    col3.metric("Call Wall", formatar(call_wall))
    col4.metric("Put Wall", formatar(put_wall))
    col5.metric("Key Level", formatar(key_level), "🔥")

    # Gráficos
    tab1, tab2, tab3, tab4 = st.tabs(["GEX Total", "GEX Descoberto", "Call vs Put", "Skew Vol"])

    with tab1:
        fig = go.Figure()
        calls = df[df['tipo']=='CALL'].groupby('strike')['gex_total'].sum()
        puts = df[df['tipo']=='PUT'].groupby('strike')['gex_total'].sum()
        fig.add_bar(x=calls.index, y=calls/1e6, name="Call GEX", marker_color="green")
        fig.add_bar(x=puts.index, y=puts/1e6, name="Put GEX", marker_color="red")
        fig.add_vline(x=spot, line_dash="dash", line_color="yellow", annotation_text=f"Spot {spot}")
        fig.update_layout(title=f"GEX Total - {ticker}", template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        desc = df.groupby('strike')['gex_desc'].sum()
        fig2.add_bar(x=desc.index, y=desc/1e6, name="GEX Descoberto", marker_color=["lime" if x>0 else "red" for x in desc])
        fig2.add_vline(x=spot, line_dash="dash", line_color="yellow")
        fig2.update_layout(title=f"GEX Descoberto - {ticker}", template="plotly_dark", height=600)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        fig3 = go.Figure()
        oi_call = df[df['tipo']=='CALL'].groupby('strike')['oi_total'].sum()
        oi_put = df[df['tipo']=='PUT'].groupby('strike')['oi_total'].sum()
        fig3.add_bar(x=oi_call.index, y=oi_call, name="OI Call", marker_color="lime")
        fig3.add_bar(x=oi_put.index, y=oi_put, name="OI Put", marker_color="red")
        fig3.update_layout(barmode='overlay', title=f"Open Interest Call vs Put - {ticker}", template="plotly_dark")
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        fig4 = go.Figure()
        vol_call = df[df['tipo']=='CALL'].groupby('strike')['vol'].mean()
        vol_put = df[df['tipo']=='PUT'].groupby('strike')['vol'].mean()
        fig4.add_scatter(x=vol_call.index, y=vol_call, mode='lines+markers', name="IV Call", line_color="green")
        fig4.add_scatter(x=vol_put.index, y=vol_put, mode='lines+markers', name="IV Put", line_color="red")
        fig4.add_vline(x=spot, line_dash="dash", line_color="yellow")
        fig4.update_layout(title="Skew de Volatilidade", template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)

    st.success(f"Dashboard {ticker} carregado com sucesso! Atualize quando quiser.")
    st.balloons()

st.markdown("---")
st.caption("Feito com muito gamma e café por quem vive de opções na B3 🇧🇷")