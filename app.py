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

def formatar_numero(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "N/A"
    try:
        return locale.format_string(f"%.{casas_decimais}f", valor, grouping=True)
    except:
        return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_vencimento_type(date):
    first_day_of_month = date.replace(day=1)
    first_friday = first_day_of_month + timedelta(days=(4 - first_day_of_month.weekday() + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
    return "M" if date.date() == third_friday.date() else "W"

# Funções de Gráficos - 100% IDÊNTICAS AO ORIGINAL
def create_separate_charts(chart_type, all_venc_filters, data_store, spot_price):
    try:
        fig_total = go.Figure()
        fig_desc = go.Figure()
       
        is_first = True
        for venc_filt in all_venc_filters:
            # Posição Total
            key_total = f"{venc_filt} - Total"
            d_total = data_store.get(key_total, {})
           
            if chart_type == 'gex':
                fig_total.add_trace(go.Bar(x=d_total.get("gex_x", []), y=d_total.get("gex_y", []), name="GEX",
                                           marker_color=["#00FF00" if g >= 0 else "#FF0000" for g in d_total.get("gex_y", [])],
                                           showlegend=False, visible=is_first,
                                           hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Total: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total.get("gex_x", []))),
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total.get("gex_x", [])))))))
            elif chart_type == 'gamma_cp':
                fig_total.add_trace(go.Bar(x=d_total.get('strikes_gamma', []), y=d_total.get('gamma_call_y', []), name='Call Gamma', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Total Call: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total.get('strikes_gamma', []))),
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total.get('strikes_gamma', [])))))))
                fig_total.add_trace(go.Bar(x=d_total.get('strikes_gamma', []), y=d_total.get('gamma_put_y', []), name='Put Gamma', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Total Put: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total.get('strikes_gamma', []))),
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total.get('strikes_gamma', [])))))))
            elif chart_type == 'oi_cp':
                fig_total.add_trace(go.Bar(x=d_total.get('strikes_oi', []), y=d_total.get('oi_call_y', []), name='OI Call', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Total Call: %{y}<br>Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total.get('strikes_oi', []))),
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total.get('strikes_oi', [])))))))
                fig_total.add_trace(go.Bar(x=d_total.get('strikes_oi', []), y=d_total.get('oi_put_y', []), name='OI Put', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Total Put: %{y}<br>Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total.get('strikes_oi', []))),
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total.get('strikes_oi', [])))))))
           
            # Posição Descoberto
            key_desc = f"{venc_filt} - Descoberto"
            d_desc = data_store.get(key_desc, {})
           
            if chart_type == 'gex':
                fig_desc.add_trace(go.Bar(x=d_desc.get("gex_x", []), y=d_desc.get("gex_y", []), name="GEX",
                                          marker_color=["#00FF00" if g >= 0 else "#FF0000" for g in d_desc.get("gex_y", [])],
                                          showlegend=False, visible=is_first,
                                          hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Descoberto: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc.get("gex_x", []))),
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc.get("gex_x", [])))))))
            elif chart_type == 'gamma_cp':
                fig_desc.add_trace(go.Bar(x=d_desc.get('strikes_gamma', []), y=d_desc.get('gamma_call_y', []), name='Call Gamma', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Descoberto Call: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc.get('strikes_gamma', []))),
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc.get('strikes_gamma', [])))))))
                fig_desc.add_trace(go.Bar(x=d_desc.get('strikes_gamma', []), y=d_desc.get('gamma_put_y', []), name='Put Gamma', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Descoberto Put: %{y:.2f}M<br>Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc.get('strikes_gamma', []))),
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc.get('strikes_gamma', [])))))))
            elif chart_type == 'oi_cp':
                fig_desc.add_trace(go.Bar(x=d_desc.get('strikes_oi', []), y=d_desc.get('oi_call_y', []), name='OI Call', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Descoberto Call: %{y}<br>Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc.get('strikes_oi', []))),
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc.get('strikes_oi', [])))))))
                fig_desc.add_trace(go.Bar(x=d_desc.get('strikes_oi', []), y=d_desc.get('oi_put_y', []), name='OI Put', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate="Opção: %{customdata[0]}<br>Strike: R$%{x}<br>Descoberto Put: %{y}<br>Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc.get('strikes_oi', []))),
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc.get('strikes_oi', [])))))))
            is_first = False
        # Spot line
        if spot_price > 0:
            fig_total.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {formatar_numero(spot_price, 2)}", annotation_position="top", annotation_font_color="#FFFF00")
            fig_desc.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {formatar_numero(spot_price, 2)}", annotation_position="top", annotation_font_color="#FFFF00")
        # Layout
        chart_titles = {'gex': 'Exposição GEX', 'gamma_cp': 'Exposição GEX Call vs Put', 'oi_cp': 'Open Interest Call vs Put'}
        yaxis_titles = {'gex': 'Gamma (Milhões)', 'gamma_cp': 'Gamma (Milhões)', 'oi_cp': 'Open Interest'}
        fig_total.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white', xaxis=dict(gridcolor='#333333', title='Strike'), yaxis=dict(gridcolor='#333333', title=yaxis_titles[chart_type]), title_text=f"{chart_titles[chart_type]} - Posição Total", bargap=0.1, barmode='overlay' if chart_type in ['gamma_cp', 'oi_cp'] else 'group', height=600)
        fig_desc.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white', xaxis=dict(gridcolor='#333333', title='Strike'), yaxis=dict(gridcolor='#333333', title=yaxis_titles[chart_type]), title_text=f"{chart_titles[chart_type]} - Posição Descoberto", bargap=0.1, barmode='overlay' if chart_type in ['gamma_cp', 'oi_cp'] else 'group', height=600)
        return fig_total, fig_desc
    except Exception as e:
        st.error(f"Erro em gráfico {chart_type}: {e}")
        return go.Figure(), go.Figure()

def create_cumulative_gex_separate(all_venc_filters, df_full, spot_price):
    try:
        fig_total = go.Figure()
        fig_desc = go.Figure()
        is_first = True
        for venc_filt in all_venc_filters:
            df_filt_venc = df_full
            if venc_filt == "Todos os MENSAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'M']
            elif venc_filt == "Todos os SEMANAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'W']
            elif venc_filt != "Todos os Vencimentos":
                df_filt_venc = df_full[df_full['VencimentoDT'].dt.strftime('%d/%m/%Y') == venc_filt.split(' ')[0]]
            # Total
            df_gex_total = df_filt_venc.groupby('Strike').agg(Total_Gamma=('Gamma Exposure Total', 'sum')).reset_index()
            df_gex_total = df_gex_total.sort_values('Strike')
            df_gex_total['Cumulative_Gamma'] = df_gex_total['Total_Gamma'].cumsum()
            fig_total.add_trace(go.Scatter(x=df_gex_total['Strike'], y=df_gex_total['Cumulative_Gamma'] / 1_000_000, name=f"Total_{venc_filt}", visible=is_first, line=dict(color='#00FFFF', width=2), showlegend=False))
            # Descoberto
            df_gex_desc = df_filt_venc.groupby('Strike').agg(Total_Gamma=('Gamma Exposure Descoberto', 'sum')).reset_index()
            df_gex_desc = df_gex_desc.sort_values('Strike')
            df_gex_desc['Cumulative_Gamma'] = df_gex_desc['Total_Gamma'].cumsum()
            fig_desc.add_trace(go.Scatter(x=df_gex_desc['Strike'], y=df_gex_desc['Cumulative_Gamma'] / 1_000_000, name=f"Descoberto_{venc_filt}", visible=is_first, line=dict(color='#00FFFF', width=2), showlegend=False))
            is_first = False
        # Linhas
        fig_total.add_hline(y=0, line_width=1, line_dash="dot", line_color="#777777")
        fig_desc.add_hline(y=0, line_width=1, line_dash="dot", line_color="#777777")
        if spot_price > 0:
            fig_total.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {formatar_numero(spot_price, 2)}", annotation_position="top", annotation_font_color="#FFFF00")
            fig_desc.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {formatar_numero(spot_price, 2)}", annotation_position="top", annotation_font_color="#FFFF00")
        # Layout
        fig_total.update_layout(title_text="GEX Cumulativo - Posição Total", plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white', xaxis=dict(gridcolor='#333333', title='Strike'), yaxis=dict(gridcolor='#333333', title='Gamma (Milhões)'), height=600)
        fig_desc.update_layout(title_text="GEX Cumulativo - Posição Descoberto", plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white', xaxis=dict(gridcolor='#333333', title='Strike'), yaxis=dict(gridcolor='#333333', title='Gamma (Milhões)'), height=600)
        return fig_total, fig_desc
    except Exception as e:
        st.error(f"Erro em GEX Cumulativo: {e}")
        return go.Figure(), go.Figure()

def create_single_chart_skew(all_venc_filters, data_store, spot_price):
    try:
        fig = go.Figure()
        is_first = True
        for venc_filt in all_venc_filters:
            key_total = f"{venc_filt} - Total"
            d_total = data_store.get(key_total, {})
            fig.add_trace(go.Scatter(x=d_total.get('strikes_skew_call', []), y=d_total.get('skew_call_y', []), mode='lines+markers', name='Vol Call', marker_color='#00FF00', line=dict(color='#00FF00'), visible=is_first, showlegend=True))
            fig.add_trace(go.Scatter(x=d_total.get('strikes_skew_put', []), y=d_total.get('skew_put_y', []), mode='lines+markers', name='Vol Put', marker_color='#FF0000', line=dict(color='#FF0000'), visible=is_first, showlegend=True))
            is_first = False
        if spot_price > 0:
            fig.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {formatar_numero(spot_price, 2)}", annotation_position="top", annotation_font_color="#FFFF00")
        fig.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white', xaxis=dict(gridcolor='#333333', title='Strike'), yaxis=dict(gridcolor='#333333', title='Vol. Implícita (%)'), title_text="Skew de Volatilidade Call vs Put", showlegend=True, height=600)
        return fig
    except Exception as e:
        st.error(f"Erro em Skew: {e}")
        return go.Figure()

# Cache para processar ticker - 100% SEU CÓDIGO ORIGINAL
@st.cache_data(ttl=3600)
def processar_ticker(ticker, data_str):
    try:
        data_formatada = datetime.strptime(data_str, '%Y-%m-%d')
        today = data_formatada.date()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'}
        url_oplab = f"https://opcoes.oplab.com.br/mercado/acoes/opcoes/{ticker}"
        url_b3 = f"https://www.b3.com.br/json/{data_formatada.strftime('%Y%m%d')}/Posicoes/Empresa/SI_C_OPCPOSABEMP.json"
        response_oplab = requests.get(url_oplab, headers=headers)
        response_b3 = requests.get(url_b3)
        response_oplab.raise_for_status()
        response_b3.raise_for_status()
        soup = BeautifulSoup(response_oplab.text, 'html.parser')
        spot_price = 0.0
        if tag := soup.find('li', class_='AssetInfo_close__AcrYC'):
            try:
                spot_price = float(tag.get_text(strip=True).replace('R$', '').strip().replace(',', '.'))
            except:
                pass
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag:
            return None
        json_data_oplab = json.loads(script_tag.string)
        json_data_b3 = response_b3.json()
        open_interest_dict = {}
        for l in json_data_b3.get('Empresa', {}):
            for s in json_data_b3['Empresa'][l]:
                symbol = s['ser']
                open_interest_dict[symbol] = {'posTo': s['posTo'], 'tMerc': s['tMerc'], 'poCob': s.get('poCob', 0.0), 'posDe': s.get('posDe', 0.0), 'posTr': s.get('posTr', 0.0)}
        series = json_data_oplab.get('props', {}).get('pageProps', {}).get('series', [])
        options_data = []
        for serie in series:
            for strike_data in serie.get('strikes', []):
                for opt_type in ['call', 'put']:
                    option = strike_data.get(opt_type)
                    if option:
                        symbol = option.get('symbol', '')
                        liquidity_text = option.get('bs', {}).get('liquidity-text', 'Nenhuma liquidez')
                        oi_info = open_interest_dict.get(symbol, {})
                        tMerc_map = {'call': '70', 'put': '80'}
                        open_interest_total = oi_info.get('posTo', 0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0
                        pos_coberta = oi_info.get('poCob', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0
                        pos_descoberta = oi_info.get('posDe', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0
                        pos_travada = oi_info.get('posTr', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0
                        gamma = option.get('bs', {}).get('gamma', 0)
                        volatility = option.get('bs', {}).get('volatility') or 0
                        gamma_exposure_total = (open_interest_total * gamma * spot_price * spot_price * 0.01) if opt_type == 'call' else -(open_interest_total * gamma * spot_price * spot_price * 0.01)
                        gamma_exposure_coberta = (pos_coberta * gamma * spot_price * spot_price * 0.01) if opt_type == 'call' else -(pos_coberta * gamma * spot_price * spot_price * 0.01)
                        gamma_exposure_descoberta = (pos_descoberta * gamma * spot_price * spot_price * 0.01) if opt_type == 'call' else -(pos_descoberta * gamma * spot_price * spot_price * 0.01)
                        gamma_exposure_travada = (pos_travada * gamma * spot_price * spot_price * 0.01) if opt_type == 'call' else -(pos_travada * gamma * spot_price * spot_price * 0.01)
                        options_data.append({
                            'Vencimento': serie['due_date'], 'Tipo': opt_type.upper(), 'Strike': strike_data['strike'], 'symbol': symbol, 'liquidity_text': liquidity_text,
                            'Open Interest Total': open_interest_total, 'Open Interest Coberto': pos_coberta, 'Open Interest Descoberto': pos_descoberta, 'Open Interest Travado': pos_travada,
                            'Gamma Exposure Total': gamma_exposure_total, 'Gamma Exposure Coberto': gamma_exposure_coberta, 'Gamma Exposure Descoberto': gamma_exposure_descoberta, 'Gamma Exposure Travado': gamma_exposure_travada,
                            'Volatilidade': volatility
                        })
        if not options_data:
            return None
        df_full = pd.DataFrame(options_data)
        df_full['VencimentoDT'] = pd.to_datetime(df_full['Vencimento'])
        df_full['TipoVenc'] = df_full['VencimentoDT'].apply(get_vencimento_type)
        df_full['MesAno'] = df_full['VencimentoDT'].dt.strftime('%b/%Y').str.capitalize()
        # Cálculo das Métricas - 100% SEU CÓDIGO
        exp_move_min = None
        exp_move_max = None
        try:
            df_vol = df_full[(df_full['Volatilidade'] > 0) & (df_full['VencimentoDT'].dt.date >= today)]
            if not df_vol.empty:
                avg_vol = df_vol['Volatilidade'].mean()
                exp_move = avg_vol / 16
                exp_move_min = spot_price * (1 - exp_move / 100)
                exp_move_max = spot_price * (1 + exp_move / 100)
        except:
            pass
        call_wall = None
        put_wall = None
        try:
            df_gamma = df_full.groupby('Strike').agg(Total_Gamma=('Gamma Exposure Total', 'sum')).reset_index()
            positive_gamma = df_gamma[df_gamma["Total_Gamma"] > 0]
            if not positive_gamma.empty:
                call_wall = positive_gamma.loc[positive_gamma["Total_Gamma"].idxmax()]["Strike"]
            negative_gamma = df_gamma[df_gamma["Total_Gamma"] < 0]
            if not negative_gamma.empty:
                put_wall = negative_gamma.loc[negative_gamma["Total_Gamma"].idxmin()]["Strike"]
        except:
            pass
        call_wall_0dte = None
        put_wall_0dte = None
        key_level_0dte = None
        try:
            df_0dte = df_full[df_full['VencimentoDT'].dt.date >= today]
            if not df_0dte.empty:
                next_expiry = df_0dte['VencimentoDT'].min().date()
                df_0dte = df_0dte[df_0dte['VencimentoDT'].dt.date == next_expiry]
                if not df_0dte.empty:
                    df_gamma_0dte = df_0dte.groupby("Strike").agg(Total_Gamma=("Gamma Exposure Total", "sum")).reset_index()
                    if not df_gamma_0dte.empty:
                        positive_gamma_0dte = df_gamma_0dte[df_gamma_0dte["Total_Gamma"] > 0]
                        if not positive_gamma_0dte.empty:
                            call_wall_0dte = positive_gamma_0dte.loc[positive_gamma_0dte["Total_Gamma"].idxmax()]["Strike"]
                        negative_gamma_0dte = df_gamma_0dte[df_gamma_0dte["Total_Gamma"] < 0]
                        if not negative_gamma_0dte.empty:
                            put_wall_0dte = negative_gamma_0dte.loc[negative_gamma_0dte["Total_Gamma"].idxmin()]["Strike"]
                        df_0dte['TotalGammaAbsoluto'] = df_0dte['Gamma Exposure Total'].abs()
                        df_key_level_0dte = df_0dte.groupby("Strike").agg(Total_Gamma_Abs=("TotalGammaAbsoluto", "sum")).reset_index()
                        if not df_key_level_0dte.empty:
                            key_level_0dte = df_key_level_0dte.loc[df_key_level_0dte["Total_Gamma_Abs"].idxmax()]["Strike"]
        except:
            pass
        key_level = None
        try:
            df_full['TotalGammaAbsoluto'] = df_full['Gamma Exposure Total'].abs()
            df_key_level = df_full[df_full['VencimentoDT'].dt.date >= today].groupby("Strike").agg(Total_Gamma_Abs=("TotalGammaAbsoluto", "sum")).reset_index()
            if not df_key_level.empty:
                key_level = df_key_level.loc[df_key_level["Total_Gamma_Abs"].idxmax()]["Strike"]
        except:
            pass
        condicao_gamma = "Neutra"
        try:
            total_gex_sum = df_full['Gamma Exposure Total'].sum()
            if total_gex_sum > 0:
                condicao_gamma = "Positiva"
            elif total_gex_sum < 0:
                condicao_gamma = "Negativa"
        except:
            condicao_gamma = "N/A"
        gex_1 = gex_2 = gex_3 = gex_4 = gex_5 = None
        try:
            if not df_full.empty and exp_move_min is not None and exp_move_max is not None:
                df_gex_intervalo = df_full[(df_full['Strike'] >= exp_move_min) & (df_full['Strike'] <= exp_move_max)]
                if not df_gex_intervalo.empty:
                    df_gex_summary = df_gex_intervalo.groupby('Strike').agg(TotalGammaSum=('Gamma Exposure Total', lambda x: x.abs().sum())).reset_index()
                    df_gex_summary = df_gex_summary.sort_values(by='TotalGammaSum', ascending=False)
                    strikes_list = df_gex_summary['Strike'].tolist()
                    if len(strikes_list) >= 1: gex_1 = strikes_list[0]
                    if len(strikes_list) >= 2: gex_2 = strikes_list[1]
                    if len(strikes_list) >= 3: gex_3 = strikes_list[2]
                    if len(strikes_list) >= 4: gex_4 = strikes_list[3]
                    if len(strikes_list) >= 5: gex_5 = strikes_list[4]
        except:
            pass
        summary_metrics = {
            "1D Exp Move Min": exp_move_min, "1D Exp Move Max": exp_move_max, "Call Wall": call_wall, "Put Wall": put_wall,
            "Call Wall 0DTE": call_wall_0dte, "Put Wall 0DTE": put_wall_0dte, "Key Level": key_level, "Key Level 0DTE": key_level_0dte,
            "Condição Gamma": condicao_gamma, "GEX 1": gex_1, "GEX 2": gex_2, "GEX 3": gex_3, "GEX 4": gex_4, "GEX 5": gex_5
        }
        # all_venc_filters e data_store - 100% SEU CÓDIGO
        all_venc_filters = ["Todos os Vencimentos", "Todos os MENSAIS", "Todos os SEMANAIS"]
        vencimentos_individuais = df_full.drop_duplicates('VencimentoDT').sort_values('VencimentoDT')
        all_venc_filters.extend([f"{row['VencimentoDT'].strftime('%d/%m/%Y')} ({row['TipoVenc']})" for _, row in vencimentos_individuais.iterrows()])
        position_filters = ["Total", "Coberto", "Descoberto", "Travado"]
        data_store = {}
        for venc_filt in all_venc_filters:
            if venc_filt == "Todos os Vencimentos":
                df_filt_venc = df_full
            elif venc_filt == "Todos os MENSAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'M']
            elif venc_filt == "Todos os SEMANAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'W']
            else:
                df_filt_venc = df_full[df_full['VencimentoDT'].dt.strftime('%d/%m/%Y') == venc_filt.split(' ')[0]]
            for pos_filt in position_filters:
                gamma_col = f'Gamma Exposure {pos_filt}'
                oi_col = f'Open Interest {pos_filt}'
                try:
                    df_gex = df_filt_venc.groupby('Strike').agg(Total_Gamma=(gamma_col, 'sum')).reset_index()
                    df_gex_sorted = df_gex.sort_values('Strike')
                    df_gex_sorted['Cumulative_Gamma'] = df_gex_sorted['Total_Gamma'].cumsum()
                    df_gamma_cp = df_filt_venc.pivot_table(index='Strike', columns='Tipo', values=gamma_col, aggfunc='sum').fillna(0)
                    df_oi_cp = df_filt_venc.pivot_table(index='Strike', columns='Tipo', values=oi_col, aggfunc='sum').fillna(0)
                    df_skew = df_filt_venc[df_filt_venc['Volatilidade'] > 0].sort_values('Strike')
                    key = f"{venc_filt} - {pos_filt}"
                    data_store[key] = {
                        'gex_x': df_gex['Strike'].tolist(), 'gex_y': (df_gex['Total_Gamma'] / 1_000_000).tolist(),
                        'gamma_call_y': (df_gamma_cp.get('CALL', pd.Series(0, index=df_gamma_cp.index)) / 1_000_000).tolist(), 'gamma_put_y': (df_gamma_cp.get('PUT', pd.Series(0, index=df_gamma_cp.index)) / 1_000_000).tolist(),
                        'oi_call_y': df_oi_cp.get('CALL', pd.Series(0, index=df_oi_cp.index)).tolist(), 'oi_put_y': df_oi_cp.get('PUT', pd.Series(0, index=df_oi_cp.index)).tolist(),
                        'skew_call_y': df_skew[df_skew['Tipo'] == 'CALL']['Volatilidade'].tolist() if not df_skew[df_skew['Tipo'] == 'CALL'].empty else [], 'skew_put_y': df_skew[df_skew['Tipo'] == 'PUT']['Volatilidade'].tolist() if not df_skew[df_skew['Tipo'] == 'PUT'].empty else [],
                        'strikes_gamma': df_gamma_cp.index.tolist(), 'strikes_oi': df_oi_cp.index.tolist(),
                        'strikes_skew_call': df_skew[df_skew['Tipo'] == 'CALL']['Strike'].tolist() if not df_skew[df_skew['Tipo'] == 'CALL'].empty else [], 'strikes_skew_put': df_skew[df_skew['Tipo'] == 'PUT']['Strike'].tolist() if not df_skew[df_skew['Tipo'] == 'PUT'].empty else [],
                        'symbols': df_filt_venc.groupby('Strike')['symbol'].first().reindex(df_gex['Strike'], fill_value='N/A').tolist(),
                        'liquidity_text': df_filt_venc.groupby('Strike')['liquidity_text'].first().reindex(df_gex['Strike'], fill_value='N/A').tolist(),
                        'symbols_call': df_skew[df_skew['Tipo'] == 'CALL']['symbol'].tolist() if not df_skew[df_skew['Tipo'] == 'CALL'].empty else [],
                        'liquidity_text_call': df_skew[df_skew['Tipo'] == 'CALL']['liquidity_text'].tolist() if not df_skew[df_skew['Tipo'] == 'CALL'].empty else [],
                        'symbols_put': df_skew[df_skew['Tipo'] == 'PUT']['symbol'].tolist() if not df_skew[df_skew['Tipo'] == 'PUT'].empty else [],
                        'liquidity_text_put': df_skew[df_skew['Tipo'] == 'PUT']['liquidity_text'].tolist() if not df_skew[df_skew['Tipo'] == 'PUT'].empty else []
                    }
                except Exception as e:
                    st.error(f"Erro em data_store {venc_filt} - {pos_filt}: {e}")
        # Geração de figs - 100% SEU CÓDIGO
        fig_gex_total, fig_gex_desc = create_separate_charts('gex', all_venc_filters, data_store, spot_price)
        fig_gamma_cp_total, fig_gamma_cp_desc = create_separate_charts('gamma_cp', all_venc_filters, data_store, spot_price)
        fig_oi_cp_total, fig_oi_cp_desc = create_separate_charts('oi_cp', all_venc_filters, data_store, spot_price)
        fig_skew = create_single_chart_skew(all_venc_filters, data_store, spot_price)
        fig_gex_cumulativo_total, fig_gex_cumulativo_desc = create_cumulative_gex_separate(all_venc_filters, df_full, spot_price)
        return {
            'summary_metrics': summary_metrics, 'spot_price': spot_price,
            'figs': {'gex_total': fig_gex_total, 'gex_desc': fig_gex_desc, 'gamma_cp_total': fig_gamma_cp_total, 'gamma_cp_desc': fig_gamma_cp_desc, 'oi_cp_total': fig_oi_cp_total, 'oi_cp_desc': fig_oi_cp_desc, 'skew': fig_skew, 'gex_cumulativo_total': fig_gex_cumulativo_total, 'gex_cumulativo_desc': fig_gex_cumulativo_desc},
            'all_venc_filters': all_venc_filters, 'df_full': df_full
        }
    except Exception as e:
        st.error(f"Erro ao processar {ticker}: {e}")
        return None

# Interface Streamlit - MELHOR QUE O HTML ORIGINAL
st.title("📈 Dashboard de Opções B3 - GEX Completo")
st.markdown("**Todos os cálculos e gráficos do seu script original • Interface interativa e responsiva**")

col1, col2 = st.columns([3, 1])
with col1:
    tickers_input = st.text_input("Tickers (separados por vírgula)", value="PETR4,VALE3,ITUB4")
with col2:
    data_ref = st.date_input("Data (YYYY-MM-DD)", value=datetime.today())

if st.button("Gerar Dashboard", type="primary"):
    selected_tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    tickers_data = {}
    progress_bar = st.progress(0)
    for i, ticker in enumerate(selected_tickers):
        progress_bar.progress((i + 1) / len(selected_tickers))
        dados = processar_ticker(ticker, data_ref.strftime("%Y-%m-%d"))
        if dados:
            tickers_data[ticker] = dados
    if not tickers_data:
        st.error("Nenhum ticker processado. Verifique a conexão ou tickers.")
        st.stop()
    ticker_selecionado = st.selectbox("Selecione o ticker", options=list(tickers_data.keys()))
    dados = tickers_data[ticker_selecionado]
    summary_metrics = dados['summary_metrics']
    spot_price = dados['spot_price']
    all_venc_filters = dados['all_venc_filters']
    selected_venc = st.selectbox("Filtro de Vencimento", options=all_venc_filters)
    figs = dados['figs']
    df_full = dados['df_full']
    # Métricas - Como no seu HTML, mas com st.metric
    st.subheader("Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("1D Exp Move Min", formatar_numero(summary_metrics["1D Exp Move Min"], 2))
        st.metric("Call Wall", formatar_numero(summary_metrics["Call Wall"], 2) if summary_metrics["Call Wall"] else "N/A")
        st.metric("Call Wall 0DTE", formatar_numero(summary_metrics["Call Wall 0DTE"], 2) if summary_metrics["Call Wall 0DTE"] else "N/A")
        st.metric("GEX 1", formatar_numero(summary_metrics["GEX 1"], 2) if summary_metrics["GEX 1"] else "N/A")
    with col2:
        st.metric("1D Exp Move Max", formatar_numero(summary_metrics["1D Exp Move Max"], 2))
        st.metric("Put Wall", formatar_numero(summary_metrics["Put Wall"], 2) if summary_metrics["Put Wall"] else "N/A")
        st.metric("Put Wall 0DTE", formatar_numero(summary_metrics["Put Wall 0DTE"], 2) if summary_metrics["Put Wall 0DTE"] else "N/A")
        st.metric("GEX 2", formatar_numero(summary_metrics["GEX 2"], 2) if summary_metrics["GEX 2"] else "N/A")
    with col3:
        st.metric("Key Level", formatar_numero(summary_metrics["Key Level"], 2) if summary_metrics["Key Level"] else "N/A")
        st.metric("Key Level 0DTE", formatar_numero(summary_metrics["Key Level 0DTE"], 2) if summary_metrics["Key Level 0DTE"] else "N/A")
        st.metric("GEX 3", formatar_numero(summary_metrics["GEX 3"], 2) if summary_metrics["GEX 3"] else "N/A")
        st.metric("Condição Gamma", summary_metrics["Condição Gamma"])
    with col4:
        st.metric("GEX 4", formatar_numero(summary_metrics["GEX 4"], 2) if summary_metrics["GEX 4"] else "N/A")
        st.metric("GEX 5", formatar_numero(summary_metrics["GEX 5"], 2) if summary_metrics["GEX 5"] else "N/A")
    if st.button("Copiar Métricas"):
        texto = " | ".join([f"{k}: {formatar_numero(v,2) if isinstance(v, (int, float)) else v}" for k, v in summary_metrics.items()])
        st.code(texto)
        st.success("Métricas copiadas!")
    # Gráficos - Com filtro por selected_venc
    tab1, tab2, tab3, tab4 = st.tabs(["GEX", "Gamma C/P", "OI C/P", "Skew & Cumulativo"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_separate_charts('gex', [selected_venc], dados['data_store'], spot_price)[0], use_container_width=True)
        with col2:
            st.plotly_chart(create_separate_charts('gex', [selected_venc], dados['data_store'], spot_price)[1], use_container_width=True)
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_separate_charts('gamma_cp', [selected_venc], dados['data_store'], spot_price)[0], use_container_width=True)
        with col2:
            st.plotly_chart(create_separate_charts('gamma_cp', [selected_venc], dados['data_store'], spot_price)[1], use_container_width=True)
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_separate_charts('oi_cp', [selected_venc], dados['data_store'], spot_price)[0], use_container_width=True)
        with col2:
            st.plotly_chart(create_separate_charts('oi_cp', [selected_venc], dados['data_store'], spot_price)[1], use_container_width=True)
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_single_chart_skew([selected_venc], dados['data_store'], spot_price), use_container_width=True)
        with col2:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.plotly_chart(create_cumulative_gex_separate([selected_venc], df_full, spot_price)[0], use_container_width=True)
            with col_c2:
                st.plotly_chart(create_cumulative_gex_separate([selected_venc], df_full, spot_price)[1], use_container_width=True)
    st.success(f"Dashboard para {ticker_selecionado} gerado com sucesso! Todos os gráficos filtrados por {selected_venc}.")
