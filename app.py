# app.py - GEX Dashboard B3 - 100% IDÊNTICO AO ORIGINAL, PAINEL STREAMLIT
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime, timedelta
import locale
import plotly.graph_objects as go
import plotly.io as pio
import traceback

# Configurações
st.set_page_config(page_title="GEX Dashboard B3", layout="wide", page_icon="📈")
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    pass

def formatar_numero(v, casas=2):
    if pd.isna(v) or v is None: return "N/A"
    try:
        return locale.format_string(f"%.{casas}f", v, grouping=True)
    except:
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_vencimento_type(date):
    first_day = date.replace(day=1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday() + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
    return "M" if date.date() == third_friday.date() else "W"

# ========================= GRÁFICOS =========================
def create_separate_charts(chart_type, filtros, data_store, spot):
    fig_total = go.Figure()
    fig_desc  = go.Figure()

    for filt in filtros:
        k_total = f"{filt} - Total"
        k_desc  = f"{filt} - Descoberto"
        d_total = data_store.get(k_total, {})
        d_desc  = data_store.get(k_desc, {})

        # === GEX ===
        if chart_type == "gex":
            if d_total.get("gex_x"):
                fig_total.add_trace(go.Bar(
                    x=d_total["gex_x"], y=d_total["gex_y"],
                    marker_color=["#00FF00" if y>=0 else "#FF0000" for y in d_total["gex_y"]],
                    name="GEX Total", showlegend=False,
                    hovertemplate="Strike: %{x}<br>GEX: %{y:.2f}M<extra></extra>"
                ))
            if d_desc.get("gex_x"):
                fig_desc.add_trace(go.Bar(
                    x=d_desc["gex_x"], y=d_desc["gex_y"],
                    marker_color=["#00FF00" if y>=0 else "#FF0000" for y in d_desc["gex_y"]],
                    name="GEX Descoberto", showlegend=False,
                    hovertemplate="Strike: %{x}<br>GEX Desc: %{y:.2f}M<extra></extra>"
                ))

        # === GAMMA CALL vs PUT ===
        elif chart_type == "gamma_cp":
            if d_total.get("strikes_gamma"):
                fig_total.add_trace(go.Bar(x=d_total["strikes_gamma"], y=d_total["gamma_call_y"], name="Call Gamma", marker_color="#00FF00", width=0.4))
                fig_total.add_trace(go.Bar(x=d_total["strikes_gamma"], y=d_total["gamma_put_y"],  name="Put Gamma",  marker_color="#FF0000", width=0.4))
            if d_desc.get("strikes_gamma"):
                fig_desc.add_trace(go.Bar(x=d_desc["strikes_gamma"], y=d_desc["gamma_call_y"], name="Call Desc", marker_color="#00FF00", width=0.4))
                fig_desc.add_trace(go.Bar(x=d_desc["strikes_gamma"], y=d_desc["gamma_put_y"],  name="Put Desc",  marker_color="#FF0000", width=0.4))

        # === OI CALL vs PUT ===
        elif chart_type == "oi_cp":
            if d_total.get("strikes_oi"):
                fig_total.add_trace(go.Bar(x=d_total["strikes_oi"], y=d_total["oi_call_y"], name="OI Call", marker_color="#00FF00", width=0.4))
                fig_total.add_trace(go.Bar(x=d_total["strikes_oi"], y=d_total["oi_put_y"],  name="OI Put",  marker_color="#FF0000", width=0.4))
            if d_desc.get("strikes_oi"):
                fig_desc.add_trace(go.Bar(x=d_desc["strikes_oi"], y=d_desc["oi_call_y"], name="OI Call Desc", marker_color="#00FF00", width=0.4))
                fig_desc.add_trace(go.Bar(x=d_desc["strikes_oi"], y=d_desc["oi_put_y"],  name="OI Put Desc",  marker_color="#FF0000", width=0.4))

    # Linha do Spot
    if spot > 0:
        for f in [fig_total, fig_desc]:
            f.add_vline(x=spot, line=dict(color="yellow", width=3, dash="dash"),
                        annotation_text=f"Spot: {formatar_numero(spot)}")

    # Layout comum
    titles = {"gex":"GEX", "gamma_cp":"Gamma Call vs Put", "oi_cp":"Open Interest Call vs Put"}
    for f, tipo in [(fig_total,"Total"), (fig_desc,"Descoberto")]:
        f.update_layout(
            template="plotly_dark", height=550, bargap=0.05,
            barmode='overlay' if chart_type != "gex" else 'group',
            title=f"{titles[chart_type]} — {tipo}",
            xaxis_title="Strike", yaxis_title="Milhões" if "gamma" in chart_type or chart_type=="gex" else "Contratos"
        )
    return fig_total, fig_desc

def create_skew_chart(filtros, data_store, spot):
    fig = go.Figure()
    for f in filtros:
        d = data_store.get(f"{f} - Total", {})
        if d.get("strikes_skew_call"):
            fig.add_trace(go.Scatter(x=d["strikes_skew_call"], y=d["skew_call_y"], mode='lines+markers', name='Vol Call', line_color='#00FF00'))
        if d.get("strikes_skew_put"):
            fig.add_trace(go.Scatter(x=d["strikes_skew_put"], y=d["skew_put_y"], mode='lines+markers', name='Vol Put', line_color='#FF0000'))
    if spot > 0:
        fig.add_vline(x=spot, line=dict(color="yellow", width=3, dash="dash"))
    fig.update_layout(template="plotly_dark", height=550, title="Skew de Volatilidade", xaxis_title="Strike", yaxis_title="Vol (%)")
    return fig

def create_cumulative_chart(filtros, df, spot):
    fig_total = go.Figure()
    fig_desc  = go.Figure()
    for f in filtros:
        df_f = df.copy()
        if "MENSAIS" in f:   df_f = df_f[df_f['TipoVenc'] == 'M']
        elif "SEMANAIS" in f:df_f = df_f[df_f['TipoVenc'] == 'W']
        elif f != "Todos os Vencimentos":
            data_sel = f.split(" ")[0]
            df_f = df_f[df_f['VencimentoDT'].dt.strftime('%d/%m/%Y') == data_sel]

        # Total
        cum = df_f.groupby('Strike')['Gamma Exposure Total'].sum().cumsum() / 1e6
        if not cum.empty:
            fig_total.add_trace(go.Scatter(x=cum.index, y=cum.values, name=f"Total {f}", line=dict(width=3)))
        # Descoberto
        cumd = df_f.groupby('Strike')['Gamma Exposure Descoberto'].sum().cumsum() / 1e6
        if not cumd.empty:
            fig_desc.add_trace(go.Scatter(x=cumd.index, y=cumd.values, name=f"Desc {f}", line=dict(width=3)))

    for fig in [fig_total, fig_desc]:
        fig.add_hline(y=0, line_dash="dot", line_color="gray")
        if spot > 0:
            fig.add_vline(x=spot, line=dict(color="yellow", width=3, dash="dash"))
        fig.update_layout(template="plotly_dark", height=550, title="GEX Cumulativo" if fig==fig_total else "GEX Cumulativo Descoberto")
    return fig_total, fig_desc

# ========================= PROCESSAMENTO =========================
@st.cache_data(ttl=3600, show_spinner="Carregando OpLab + B3...")
def processar(ticker: str, data_ref: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    url_oplab = f"https://opcoes.oplab.com.br/mercado/acoes/opcoes/{ticker}"
    url_b3_date = data_ref.replace("-", "")
    url_b3 = f"https://www.b3.com.br/json/{url_b3_date}/Posicoes/Empresa/SI_C_OPCPOSABEMP.json"

    try:
        r1 = requests.get(url_oplab, headers=headers, timeout=25)
        r2 = requests.get(url_b3, timeout=25)
        r1.raise_for_status(); r2.raise_for_status()
    except:
        return None

    soup = BeautifulSoup(r1.text, 'html.parser')
    spot = 0.0
    tag = soup.find('li', class_='AssetInfo_close__AcrYC')
    if tag:
        try:
            spot = float(tag.get_text(strip=True).replace("R$", "").replace(".", "").replace(",", "."))
        except: pass

    script = soup.find('script', id='__NEXT_DATA__')
    if not script: return None
    oplab = json.loads(script.string)
    b3 = r2.json()

    oi_dict = {}
    for empresa in b3.get('Empresa', {}).values():
        for item in empresa:
            oi_dict[item['ser']] = item

    rows = []
    for serie in oplab['props']['pageProps']['series']:
        venc = serie['due_date']
        for strike_data in serie.get('strikes', []):
            for tipo in ['call','put']:
                opt = strike_data.get(tipo)
                if not opt: continue
                sym = opt['symbol']
                info = oi_dict.get(sym, {})
                if (tipo=='call' and info.get('tMerc')!='70') or (tipo=='put' and info.get('tMerc')!='80'): continue

                gamma = opt.get('bs', {}).get('gamma', 0) or 0
                oi_total = info.get('posTo', 0)
                oi_cob   = info.get('poCob', 0)
                oi_desc  = info.get('posDe', 0)

                sign = 1 if tipo=='call' else -1
                gex_total = sign * oi_total * gamma * spot * spot * 0.01
                gex_cob   = sign * oi_cob   * gamma * spot * spot * 0.01
                gex_desc  = sign * oi_desc  * gamma * spot * spot * 0.01

                rows.append({
                    'Vencimento':venc, 'Tipo':tipo.upper(), 'Strike':strike_data['strike'],
                    'Gamma Exposure Total':gex_total, 'Gamma Exposure Coberto':gex_cob,
                    'Gamma Exposure Descoberto':gex_desc,
                    'Open Interest Total':oi_total, 'Open Interest Coberto':oi_cob,
                    'Open Interest Descoberto':oi_desc,
                    'Volatilidade': opt.get('bs', {}).get('volatility') or 0
                })

    if not rows: return None
    df = pd.DataFrame(rows)
    df['VencimentoDT'] = pd.to_datetime(df['Vencimento'])
    df['TipoVenc'] = df['VencimentoDT'].apply(get_vencimento_type)

    # Métricas (100% igual ao seu)
    gex_strike = df.groupby('Strike')['Gamma Exposure Total'].sum()
    call_wall = gex_strike[gex_strike>0].idxmax() if not gex_strike[gex_strike>0].empty else None
    put_wall  = gex_strike[gex_strike<0].idxmin() if not gex_strike[gex_strike<0].empty else None
    key_level = df.groupby('Strike')['Gamma Exposure Total'].apply(lambda x: abs(x).sum()).idxmax()
    total_gex = gex_strike.sum() / 1e6
    cond_gamma = "POSITIVA" if total_gex>0 else "NEGATIVA" if total_gex<0 else "NEUTRA"

    # data_store — FIXADO PARA NUNCA DAR KeyError
    data_store = {}
    filtros = ["Todos os Vencimentos","Todos os MENSAIS","Todos os SEMANAIS"]
    for v in df['VencimentoDT'].dt.strftime('%d/%m/%Y').unique():
        filtros.append(f"{v} ({df[df['VencimentoDT'].dt.strftime('%d/%m/%Y')==v]['TipoVenc'].iloc[0]})")

    for f in filtros:
        if f == "Todos os Vencimentos": df_f = df
        elif f == "Todos os MENSAIS": df_f = df[df['TipoVenc']=='M']
        elif f == "Todos os SEMANAIS": df_f = df[df['TipoVenc']=='W']
        else:
            df_f = df[df['VencimentoDT'].dt.strftime('%d/%m/%Y') == f.split(" ")[0]]

        for pos, suffix in [("Total","Total"), ("Descoberto","Descoberto")]:
            gamma_col = f"Gamma Exposure {pos}"
            oi_col    = f"Open Interest {pos}"

            # GEX
            gex = df_f.groupby('Strike')[gamma_col].sum()
            # Gamma C/P
            gamma_cp = df_f.pivot_table(index='Strike', columns='Tipo', values=gamma_col, aggfunc='sum', fill_value=0)
            # OI C/P
            oi_cp = df_f.pivot_table(index='Strike', columns='Tipo', values=oi_col, aggfunc='sum', fill_value=0)
            # Skew
            skew = df_f[df_f['Volatilidade']>0]

            key = f"{f} - {suffix}"
            data_store[key] = {
                "gex_x": gex.index.tolist(),
                "gex_y": (gex/1e6).tolist(),
                "strikes_gamma": gamma_cp.index.tolist(),
                "gamma_call_y": (gamma_cp.get('CALL', pd.Series(0, index=gamma_cp.index))/1e6).tolist(),
                "gamma_put_y":  (gamma_cp.get('PUT',  pd.Series(0, index=gamma_cp.index))/1e6).tolist(),
                "strikes_oi": oi_cp.index.tolist(),
                "oi_call_y": oi_cp.get('CALL', pd.Series(0, index=oi_cp.index)).tolist(),
                "oi_put_y":  oi_cp.get('PUT',  pd.Series(0, index=oi_cp.index)).tolist(),
                "strikes_skew_call": skew[skew['Tipo']=='CALL']['Strike'].tolist(),
                "skew_call_y": skew[skew['Tipo']=='CALL']['Volatilidade'].tolist(),
                "strikes_skew_put":  skew[skew['Tipo']=='PUT']['Strike'].tolist(),
                "skew_put_y":  skew[skew['Tipo']=='PUT']['Volatilidade'].tolist(),
            }

    return {
        "spot": spot,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "key_level": key_level,
        "cond_gamma": cond_gamma,
        "total_gex": round(total_gex, 2),
        "df": df,
        "data_store": data_store,
        "filtros": filtros
    }

# ========================= INTERFACE =========================
c1, c2 = st.columns([3,1])
with c1:
    tickers = st.text_input("Tickers (vírgula)", "PETR4,VALE3,ITUB4,BBDC4")
with c2:
    data_ref = st.date_input("Data", datetime.today())

if st.button("GERAR DASHBOARD COMPLETO", type="primary", use_container_width=True):
    lista = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    resultados = {}
    barra = st.progress(0)
    for i, tk in enumerate(lista):
        res = processar(tk, data_ref.strftime("%Y-%m-%d"))
        if res:
            resultados[tk] = res
        barra.progress((i+1)/len(lista))

    if not resultados:
        st.error("Nenhum ativo carregado")
        st.stop()

    ativo = st.selectbox("Ativo", options=list(resultados))
    d = resultados[ativo]
    spot = d["spot"]
    filtros = d["filtros"]
    filtro = st.selectbox("Filtro de vencimento", filtros, index=0)

    # Métricas
    st.subheader(f"Métricas — {ativo}")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Spot", formatar_numero(spot))
    m2.metric("Call Wall", formatar_numero(d["call_wall"]))
    m3.metric("Put Wall", formatar_numero(d["put_wall"]))
    m4.metric("Key Level", formatar_numero(d["key_level"]))
    m5.metric("GEX Total", f"{d['total_gex']:+.1f}M", d["cond_gamma"])

    t1, t2, t3, t4 = st.tabs(["GEX", "Gamma C/P", "Open Interest", "Skew + Cumulativo"])

    with t1:
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(create_separate_charts("gex", [filtro], d["data_store"], spot)[0], use_container_width=True)
        with c2: st.plotly_chart(create_separate_charts("gex", [filtro], d["data_store"], spot)[1], use_container_width=True)

    with t2:
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(create_separate_charts("gamma_cp", [filtro], d["data_store"], spot)[0], use_container_width=True)
        with c2: st.plotly_chart(create_separate_charts("gamma_cp", [filtro], d["data_store"], spot)[1], use_container_width=True)

    with t3:
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(create_separate_charts("oi_cp", [filtro], d["data_store"], spot)[0], use_container_width=True)
        with c2: st.plotly_chart(create_separate_charts("oi_cp", [filtro], d["data_store"], spot)[1], use_container_width=True)

    with t4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_skew_chart([filtro], d["data_store"], spot), use_container_width=True)
        with col2:
            cum_total, cum_desc = create_cumulative_chart([filtro], d["df"], spot)
            st.plotly_chart(cum_total, use_container_width=True)
            st.plotly_chart(cum_desc, use_container_width=True)

    st.success(f"Dashboard {ativo} carregado com sucesso!")
    st.balloons()

else:
    st.info("Preencha os tickers e a data → clique em GERAR DASHBOARD COMPLETO")
