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
import uuid

# --- Configurações Iniciais ---
# Configuração do locale para formatação de números
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    # Fallback para sistemas que não possuem o locale pt_BR.UTF-8 (ex: alguns ambientes Docker)
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Aviso: Locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252' não encontrado. Usando formatação padrão.")

# Definição do layout da página
st.set_page_config(layout="wide", page_title="Dashboard de Opções - GEX Calculator")

def formatar_numero(valor, casas_decimais=2):
    """
    Formata um número para o padrão brasileiro (vírgula como separador decimal).
    """
    if pd.isna(valor) or valor is None: return "N/A"
    try:
        # Tenta usar o locale configurado
        return locale.format_string(f"%.{casas_decimais}f", valor, grouping=True)
    except (NameError, TypeError, AttributeError):
        # Fallback para formatação manual
        return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# >>> ADICIONE ESTA FUNÇÃO AQUI <<<
def formatar_para_copia(valor, casas_decimais=2):
    """
    Formata um número para o padrão americano (ponto decimal)
    e retorna o valor como string, sem separador de milhar.
    """
    if isinstance(valor, (float, int)) and valor is not None:
        # Usa f-string para formatar com ponto decimal e duas casas decimais
        return f"{valor:.{casas_decimais}f}"
    return "N/A"
# >>> FIM DA ADIÇÃO <<<


def get_vencimento_type(date):
    """
    Determina se o vencimento é Mensal (M) ou Semanal (W).
    (Lógica mantida do código original, mas com o ajuste para datetime.date)
    """
    first_day_of_month = date.replace(day=1)
    # 4 é o weekday para sexta-feira (0=segunda, 6=domingo)
    first_friday = first_day_of_month + timedelta(days=(4 - first_day_of_month.weekday() + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
    # Compara apenas a data
    return "M" if date.date() == third_friday.date() else "W"

# --- Funções de Geração de Gráficos Plotly (MANTIDAS EXATAMENTE IGUAIS) ---

# --- Função para Criar Gráficos Separados para Total e Descoberto ---
def create_separate_charts(chart_type, all_venc_filters, data_store, spot_price):
    try:
        fig_total = go.Figure()
        fig_desc = go.Figure()
        
        is_first = True
        for venc_filt in all_venc_filters:
            # Posição Total
            key_total = f"{venc_filt} - Total"
            d_total = data_store[key_total]
            
            # Garante que os arrays de dados sejam processáveis, mesmo vazios
            gex_y_total = d_total["gex_y"] if 'gex_y' in d_total else []
            strikes_gamma_total = d_total.get('strikes_gamma', [])
            gamma_call_y_total = d_total.get('gamma_call_y', [])
            gamma_put_y_total = d_total.get('gamma_put_y', [])
            strikes_oi_total = d_total.get('strikes_oi', [])
            oi_call_y_total = d_total.get('oi_call_y', [])
            oi_put_y_total = d_total.get('oi_put_y', [])
            
            if chart_type == 'gex':
                fig_total.add_trace(go.Bar(x=d_total["gex_x"], y=gex_y_total, name="GEX",
                                           marker_color=["#00FF00" if g >= 0 else "#FF0000" for g in gex_y_total],
                                           showlegend=False, visible=is_first,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total: %{y:.2f}M<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(d_total["gex_x"])), 
                                                               d_total.get('liquidity_text', ['N/A'] * len(d_total["gex_x"]))))))
            elif chart_type == 'gamma_cp':
                fig_total.add_trace(go.Bar(x=strikes_gamma_total, y=gamma_call_y_total, name='Call Gamma', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total Call: %{y:.2f}M<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(strikes_gamma_total)), 
                                                               d_total.get('liquidity_text', ['N/A'] * len(strikes_gamma_total))))))
                fig_total.add_trace(go.Bar(x=strikes_gamma_total, y=gamma_put_y_total, name='Put Gamma', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total Put: %{y:.2f}M<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(strikes_gamma_total)), 
                                                               d_total.get('liquidity_text', ['N/A'] * len(strikes_gamma_total))))))
            elif chart_type == 'oi_cp':
                fig_total.add_trace(go.Bar(x=strikes_oi_total, y=oi_call_y_total, name='OI Call', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total Call: %{y}<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(strikes_oi_total)), 
                                                               d_total.get('liquidity_text', ['N/A'] * len(strikes_oi_total))))))
                fig_total.add_trace(go.Bar(x=strikes_oi_total, y=oi_put_y_total, name='OI Put', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total Put: %{y}<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(d_total.get('symbols', ['N/A'] * len(strikes_oi_total)), 
                                                               d_total.get('liquidity_text', ['N/A'] * len(strikes_oi_total))))))
            
            # Posição Descoberto
            key_desc = f"{venc_filt} - Descoberto"
            d_desc = data_store[key_desc]
            
            gex_y_desc = d_desc["gex_y"] if 'gex_y' in d_desc else []
            strikes_gamma_desc = d_desc.get('strikes_gamma', [])
            gamma_call_y_desc = d_desc.get('gamma_call_y', [])
            gamma_put_y_desc = d_desc.get('gamma_put_y', [])
            strikes_oi_desc = d_desc.get('strikes_oi', [])
            oi_call_y_desc = d_desc.get('oi_call_y', [])
            oi_put_y_desc = d_desc.get('oi_put_y', [])

            if chart_type == 'gex':
                fig_desc.add_trace(go.Bar(x=d_desc["gex_x"], y=gex_y_desc, name="GEX",
                                          marker_color=["#00FF00" if g >= 0 else "#FF0000" for g in gex_y_desc],
                                          showlegend=False, visible=is_first,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto: %{y:.2f}M<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(d_desc["gex_x"])), 
                                                              d_desc.get('liquidity_text', ['N/A'] * len(d_desc["gex_x"]))))))
            elif chart_type == 'gamma_cp':
                fig_desc.add_trace(go.Bar(x=strikes_gamma_desc, y=gamma_call_y_desc, name='Call Gamma', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto Call: %{y:.2f}M<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(strikes_gamma_desc)), 
                                                              d_desc.get('liquidity_text', ['N/A'] * len(strikes_gamma_desc))))))
                fig_desc.add_trace(go.Bar(x=strikes_gamma_desc, y=gamma_put_y_desc, name='Put Gamma', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto Put: %{y:.2f}M<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(strikes_gamma_desc)), 
                                                              d_desc.get('liquidity_text', ['N/A'] * len(strikes_gamma_desc))))))
            elif chart_type == 'oi_cp':
                fig_desc.add_trace(go.Bar(x=strikes_oi_desc, y=oi_call_y_desc, name='OI Call', marker_color='#00FF00', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto Call: %{y}<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(strikes_oi_desc)), 
                                                              d_desc.get('liquidity_text', ['N/A'] * len(strikes_oi_desc))))))
                fig_desc.add_trace(go.Bar(x=strikes_oi_desc, y=oi_put_y_desc, name='OI Put', marker_color='#FF0000', width=0.4, visible=is_first, showlegend=is_first,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto Put: %{y}<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(d_desc.get('symbols', ['N/A'] * len(strikes_oi_desc)), 
                                                              d_desc.get('liquidity_text', ['N/A'] * len(strikes_oi_desc))))))

            is_first = False

        # Adiciona linha do Spot Price em ambos
        if spot_price > 0:
            spot_price_formatted = formatar_numero(spot_price, 2)
            fig_total.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {spot_price_formatted}", annotation_position="top", annotation_font_color="#FFFF00")
            fig_desc.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {spot_price_formatted}", annotation_position="top", annotation_font_color="#FFFF00")

        # Define o layout para ambos
        chart_titles = {
            'gex': 'Exposição GEX',
            'gamma_cp': 'Exposição GEX Call vs Put',
            'oi_cp': 'Open Interest Call vs Put'
        }
        yaxis_titles = {
            'gex': 'Gamma (Milhões)',
            'gamma_cp': 'Gamma (Milhões)',
            'oi_cp': 'Open Interest'
        }
        fig_total.update_layout(
            plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white',
            xaxis=dict(gridcolor='#333333', title='Strike'),
            yaxis=dict(gridcolor='#333333', title=f"{yaxis_titles[chart_type]}"),
            title_text=f"{chart_titles[chart_type]} - Posição Total",
            bargap=0.1, barmode='overlay' if chart_type in ['gamma_cp', 'oi_cp'] else 'group',
            autosize=True, height=500
        )
        fig_desc.update_layout(
            plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white',
            xaxis=dict(gridcolor='#333333', title='Strike'),
            yaxis=dict(gridcolor='#333333', title=f"{yaxis_titles[chart_type]}"),
            title_text=f"{chart_titles[chart_type]} - Posição Descoberto",
            bargap=0.1, barmode='overlay' if chart_type in ['gamma_cp', 'oi_cp'] else 'group',
            autosize=True, height=500
        )
        
        return fig_total, fig_desc
    except Exception as e:
        st.error(f"Erro ao criar gráficos {chart_type}: {e}")
        return None, None

# --- Função para GEX Cumulativo com Gráficos Separados ---
def create_cumulative_gex_separate(all_venc_filters, df_full, spot_price):
    try:
        fig_total = go.Figure()
        fig_desc = go.Figure()

        is_first = True
        for venc_filt in all_venc_filters:
            df_filt_venc = df_full.copy()
            
            if venc_filt == "Todos os MENSAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'M'].copy()
            elif venc_filt == "Todos os SEMANAIS":
                df_filt_venc = df_full[df_full['TipoVenc'] == 'W'].copy()
            elif venc_filt != "Todos os Vencimentos":
                # Filtra pela data exata
                data_str = venc_filt.split(' ')[0]
                df_filt_venc = df_full[df_full['VencimentoDT'].dt.strftime('%d/%m/%Y') == data_str].copy()
            
            if df_filt_venc.empty:
                is_first = False
                continue

            # Posição Total
            df_gex_total = df_filt_venc.groupby('Strike').agg(Total_Gamma=('Gamma Exposure Total', 'sum')).reset_index()
            df_gex_total = df_gex_total.sort_values('Strike')
            df_gex_total['Cumulative_Gamma'] = df_gex_total['Total_Gamma'].cumsum()
            
            # Correção para customdata para corresponder ao df_gex_total
            strikes_total = df_gex_total['Strike'].tolist()
            symbols_total = df_filt_venc.groupby('Strike')['symbol'].first().reindex(strikes_total, fill_value='N/A').tolist()
            liquidity_text_total = df_filt_venc.groupby('Strike')['liquidity_text'].first().reindex(strikes_total, fill_value='N/A').tolist()

            fig_total.add_trace(go.Scatter(x=df_gex_total['Strike'], y=df_gex_total['Cumulative_Gamma'] / 1_000_000,
                                           name=f"Total_{venc_filt}", visible=is_first, 
                                           line=dict(color='#00FFFF', width=2), showlegend=False,
                                           hovertemplate=
                                           "Opção: %{customdata[0]}<br>" +
                                           "Strike: R$%{x}<br>" +
                                           "Total: %{y:.2f}M<br>" +
                                           "Liquidez: %{customdata[1]}<br>",
                                           customdata=list(zip(symbols_total, liquidity_text_total))))

            # Posição Descoberto
            df_gex_desc = df_filt_venc.groupby('Strike').agg(Total_Gamma=('Gamma Exposure Descoberto', 'sum')).reset_index()
            df_gex_desc = df_gex_desc.sort_values('Strike')
            df_gex_desc['Cumulative_Gamma'] = df_gex_desc['Total_Gamma'].cumsum()
            
            # Correção para customdata para corresponder ao df_gex_desc
            strikes_desc = df_gex_desc['Strike'].tolist()
            symbols_desc = df_filt_venc.groupby('Strike')['symbol'].first().reindex(strikes_desc, fill_value='N/A').tolist()
            liquidity_text_desc = df_filt_venc.groupby('Strike')['liquidity_text'].first().reindex(strikes_desc, fill_value='N/A').tolist()

            fig_desc.add_trace(go.Scatter(x=df_gex_desc['Strike'], y=df_gex_desc['Cumulative_Gamma'] / 1_000_000,
                                          name=f"Descoberto_{venc_filt}", visible=is_first, 
                                          line=dict(color='#00FFFF', width=2), showlegend=False,
                                          hovertemplate=
                                          "Opção: %{customdata[0]}<br>" +
                                          "Strike: R$%{x}<br>" +
                                          "Descoberto: %{y:.2f}M<br>" +
                                          "Liquidez: %{customdata[1]}<br>",
                                          customdata=list(zip(symbols_desc, liquidity_text_desc))))
            
            is_first = False

        # Adiciona linha em Y=0 em ambos
        fig_total.add_hline(y=0, line_width=1, line_dash="dot", line_color="#777777")
        fig_desc.add_hline(y=0, line_width=1, line_dash="dot", line_color="#777777")
        
        # Adiciona linha do Spot Price com a anotação
        if spot_price > 0:
            spot_price_formatted = formatar_numero(spot_price, 2)
            fig_total.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", 
                                annotation_text=f"Spot Price: {spot_price_formatted}", 
                                annotation_position="top", annotation_font_color="#FFFF00")
            fig_desc.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", 
                               annotation_text=f"Spot Price: {spot_price_formatted}", 
                               annotation_position="top", annotation_font_color="#FFFF00")
        
        fig_total.update_layout(
            title_text=f"GEX Cumulativo - Fluxo de pressão - Posição Total",
            plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white',
            xaxis=dict(gridcolor='#333333', title='Strike'),
            yaxis=dict(gridcolor='#333333', title='Gamma (Milhões)'),
            autosize=True, height=500
        )
        fig_desc.update_layout(
            title_text=f"GEX Cumulativo - Fluxo de pressão - Posição Descoberto",
            plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white',
            xaxis=dict(gridcolor='#333333', title='Strike'),
            yaxis=dict(gridcolor='#333333', title='Gamma (Milhões)'),
            autosize=True, height=500
        )
        return fig_total, fig_desc
    except Exception as e:
        st.error(f"Erro ao criar gráficos GEX Cumulativo: {e}")
        traceback.print_exc()
        return None, None

# --- Função para Skew de Volatilidade (Gráfico Único) ---
def create_single_chart_skew(all_venc_filters, data_store, spot_price):
    try:
        fig = go.Figure()
        
        is_first = True
        for venc_filt in all_venc_filters:
            key_total = f"{venc_filt} - Total"
            d_total = data_store[key_total]

            # Garante que os arrays de dados sejam processáveis, mesmo vazios
            strikes_call = d_total.get('strikes_skew_call', [])
            skew_call_y = d_total.get('skew_call_y', [])
            symbols_call = d_total.get('symbols_call', ['N/A'] * len(strikes_call))
            liquidity_text_call = d_total.get('liquidity_text_call', ['N/A'] * len(strikes_call))
            
            strikes_put = d_total.get('strikes_skew_put', [])
            skew_put_y = d_total.get('skew_put_y', [])
            symbols_put = d_total.get('symbols_put', ['N/A'] * len(strikes_put))
            liquidity_text_put = d_total.get('liquidity_text_put', ['N/A'] * len(strikes_put))

            fig.add_trace(go.Scatter(x=strikes_call, y=skew_call_y, mode='lines+markers', name='Vol Call', 
                                     marker_color='#00FF00', line=dict(color='#00FF00'), visible=is_first, showlegend=True,
                                     hovertemplate=
                                     "Opção: %{customdata[0]}<br>" +
                                     "Strike: R$%{x}<br>" +
                                     "IV Call: %{y:.2f}%<br>" +
                                     "Liquidez: %{customdata[1]}<br>",
                                     customdata=list(zip(symbols_call, liquidity_text_call))))
            fig.add_trace(go.Scatter(x=strikes_put, y=skew_put_y, mode='lines+markers', name='Vol Put', 
                                     marker_color='#FF0000', line=dict(color='#FF0000'), visible=is_first, showlegend=True,
                                     hovertemplate=
                                     "Opção: %{customdata[0]}<br>" +
                                     "Strike: R$%{x}<br>" +
                                     "IV Put: %{y:.2f}%<br>" +
                                     "Liquidez: %{customdata[1]}<br>",
                                     customdata=list(zip(symbols_put, liquidity_text_put))))
            
            is_first = False

        if spot_price > 0:
            spot_price_formatted = formatar_numero(spot_price, 2)
            fig.add_vline(x=spot_price, line_width=2, line_dash="dash", line_color="#FFFF00", annotation_text=f"Spot Price: {spot_price_formatted}", annotation_position="top", annotation_font_color="#FFFF00")

        fig.update_layout(
            plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='white',
            xaxis=dict(gridcolor='#333333', title='Strike'),
            yaxis=dict(gridcolor='#333333', title='Vol. Implícita (%)'),
            title_text=f"Skew de Volatilidade Call vs Put",
            showlegend=True,
            autosize=True, height=500
        )
        
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico de Skew: {e}")
        return None

# --- Função principal do Streamlit ---

@st.cache_data(show_spinner="Buscando e processando dados...", ttl=3600)
def fetch_and_process_data(selected_tickers, data_formatada):
    """
    Função para buscar e processar os dados, cacheada pelo Streamlit
    para evitar requisições repetidas na interação do usuário.
    """
    st.write(f"Iniciando busca e processamento para a data: {data_formatada.strftime('%Y-%m-%d')}")
    today = data_formatada.date()
    tickers_data = {}

    for ticker in selected_tickers:
        st.info(f"Processando {ticker}...")
        try:
            # --- Coleta de Dados ---
            url_oplab = f"https://opcoes.oplab.com.br/mercado/acoes/opcoes/{ticker}"
            # O URL da B3 usa o formato YYYYMMDD
            url_b3 = f"https://www.b3.com.br/json/{data_formatada.strftime('%Y%m%d')}/Posicoes/Empresa/SI_C_OPCPOSABEMP.json"
            
            # Headers mantidos do script original
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Referer': 'https://www.google.com/',
                'Cache-Control': 'max-age=0',
                'TE': 'trailers'
            }

            response_oplab = requests.get(url_oplab, headers=headers)
            response_oplab.raise_for_status()
            
            # A B3 pode falhar se a data não tiver dados
            response_b3 = requests.get(url_b3)
            if response_b3.status_code == 404:
                st.warning(f"Aviso para {ticker}: Dados da B3 (Open Interest) não encontrados para a data {data_formatada.strftime('%d/%m/%Y')}. Open Interest será 0.")
                json_data_b3 = {'Empresa': {}} # Objeto JSON vazio para evitar erro de decodificação
            else:
                response_b3.raise_for_status()
                json_data_b3 = response_b3.json()

            # --- Processamento dos Dados ---
            soup = BeautifulSoup(response_oplab.text, 'html.parser')
            spot_price = 0.0
            if (tag := soup.find('li', class_='AssetInfo_close__AcrYC')):
                try:
                    # Extração do Spot Price
                    spot_price_text = tag.find('ul').text.replace('R$', '').strip().replace(',', '.')
                    spot_price = float(spot_price_text)
                except (ValueError, AttributeError):
                    st.warning(f"Aviso para {ticker}: Spot price não encontrado. Usando valor padrão (0) para cálculos.")

            if not (script_tag := soup.find('script', id='__NEXT_DATA__')):
                st.error(f"Erro crítico para {ticker}: Estrutura do site Oplab pode ter mudado.")
                continue

            try:
                json_data_oplab = json.loads(script_tag.string)
            except json.JSONDecodeError as e:
                st.error(f"Erro ao decodificar JSON da OpLab para {ticker}: {e}")
                continue

            open_interest_dict = {}
            # Lógica de processamento dos dados B3
            for l in json_data_b3.get('Empresa', {}):
                for s in json_data_b3['Empresa'][l]:
                    symbol = s['ser']
                    open_interest_dict[symbol] = {
                        'posTo': s['posTo'],
                        'tMerc': s['tMerc'],
                        'poCob': s.get('poCob', 0.0),
                        'posDe': s.get('posDe', 0.0),
                        'posTr': s.get('posTr', 0.0)
                    }

            series = json_data_oplab.get('props', {}).get('pageProps', {}).get('series', [])
            options_data = []

            # Lógica de iteração sobre as séries e strikes da OpLab
            for serie in series:
                for strike_data in serie.get('strikes', []):
                    for opt_type in ['call', 'put']:
                        if (option := strike_data.get(opt_type)):
                            symbol = option.get('symbol', '')
                            liquidity_text = option.get('bs', {}).get('liquidity-text', 'Nenhuma liquidez')
                            oi_info = open_interest_dict.get(symbol, {})
                            tMerc_map = {'call': '70', 'put': '80'}

                            # Extração de Open Interest
                            open_interest_total = oi_info.get('posTo', 0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0
                            pos_coberta = oi_info.get('poCob', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0
                            pos_descoberta = oi_info.get('posDe', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0
                            pos_travada = oi_info.get('posTr', 0.0) if oi_info.get('tMerc') == tMerc_map[opt_type] else 0.0

                            gamma = option.get('bs', {}).get('gamma', 0)
                            volatility_value = option.get('bs', {}).get('volatility')
                            volatility = volatility_value or 0

                            # Cálculo da Gamma Exposure (MANTIDO EXATAMENTE IGUAL)
                            # Se spot_price for 0, gex será 0
                            if spot_price > 0:
                                gamma_exposure_base = gamma * spot_price * spot_price * 0.01
                                if opt_type == 'call':
                                    gamma_exposure_total = open_interest_total * gamma_exposure_base
                                    gamma_exposure_coberta = pos_coberta * gamma_exposure_base
                                    gamma_exposure_descoberta = pos_descoberta * gamma_exposure_base
                                    gamma_exposure_travada = pos_travada * gamma_exposure_base
                                else: # put
                                    gamma_exposure_total = -(open_interest_total * gamma_exposure_base)
                                    gamma_exposure_coberta = -(pos_coberta * gamma_exposure_base)
                                    gamma_exposure_descoberta = -(pos_descoberta * gamma_exposure_base)
                                    gamma_exposure_travada = -(pos_travada * gamma_exposure_base)
                            else:
                                gamma_exposure_total = gamma_exposure_coberta = gamma_exposure_descoberta = gamma_exposure_travada = 0.0

                            options_data.append({
                                'Vencimento': serie['due_date'],
                                'Tipo': opt_type.upper(),
                                'Strike': strike_data['strike'],
                                'symbol': symbol,
                                'liquidity_text': liquidity_text,
                                'Open Interest Total': open_interest_total,
                                'Open Interest Coberto': pos_coberta,
                                'Open Interest Descoberto': pos_descoberta,
                                'Open Interest Travado': pos_travada,
                                'Gamma Exposure Total': gamma_exposure_total,
                                'Gamma Exposure Coberto': gamma_exposure_coberta,
                                'Gamma Exposure Descoberto': gamma_exposure_descoberta,
                                'Gamma Exposure Travado': gamma_exposure_travada,
                                'Volatilidade': volatility
                            })

            if not options_data:
                st.warning(f"Aviso para {ticker}: Nenhum dado de opções encontrado.")
                continue

            df_full = pd.DataFrame(options_data)
            df_full['VencimentoDT'] = pd.to_datetime(df_full['Vencimento'])
            df_full['TipoVenc'] = df_full['VencimentoDT'].apply(get_vencimento_type)
            df_full['MesAno'] = df_full['VencimentoDT'].dt.strftime('%b/%Y').str.capitalize()

            # --- Cálculo das Métricas ---
            
            # 1D Exp Move (mantido igual)
            exp_move_min = None
            exp_move_max = None
            try:
                if spot_price > 0:
                    df_vol = df_full[(df_full['Volatilidade'] > 0) & (df_full['VencimentoDT'].dt.date >= today)]
                    if not df_vol.empty:
                        avg_vol = df_vol['Volatilidade'].mean()
                        exp_move = avg_vol / 16 # Formula: Vol / sqrt(252/1) = Vol / 15.87 ~ Vol / 16
                        exp_move_min = spot_price * (1 - exp_move / 100)
                        exp_move_max = spot_price * (1 + exp_move / 100)
            except Exception as e:
                st.warning(f"Erro ao calcular 1D Exp Move para {ticker}: {e}")

            # CALL WALL e PUT WALL (mantido igual)
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
            except Exception as e:
                st.warning(f"Erro ao calcular Call Wall e Put Wall para {ticker}: {e}")

            # Métricas 0DTE (mantido igual)
            call_wall_0dte = None
            put_wall_0dte = None
            key_level_0dte = None
            try:
                # Usa a primeira data de vencimento >= hoje
                df_0dte = df_full[df_full['VencimentoDT'].dt.date >= today].copy()
                if not df_0dte.empty:
                    next_expiry = df_0dte['VencimentoDT'].min().date()
                    df_0dte = df_0dte[df_0dte['VencimentoDT'].dt.date == next_expiry].copy()
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
                    else:
                        st.warning(f"Aviso para {ticker}: Nenhum dado para a data de vencimento mais próxima. Métricas 0DTE definidas como N/A.")
                else:
                    st.warning(f"Aviso para {ticker}: Nenhum dado para vencimentos a partir da data fornecida. Métricas 0DTE definidas como N/A.")
            except Exception as e:
                st.warning(f"Erro ao calcular métricas 0DTE para {ticker}: {e}")

            # KEY_LEVEL (mantido igual)
            key_level = None
            try:
                df_full['TotalGammaAbsoluto'] = df_full['Gamma Exposure Total'].abs()
                df_key_level = df_full[df_full['VencimentoDT'].dt.date >= today].groupby("Strike").agg(Total_Gamma_Abs=("TotalGammaAbsoluto", "sum")).reset_index()
                if not df_key_level.empty:
                    key_level = df_key_level.loc[df_key_level["Total_Gamma_Abs"].idxmax()]["Strike"]
                else:
                    st.warning(f"Aviso para {ticker}: Nenhum dado para vencimentos a partir da data fornecida. Key Level definido como N/A.")
            except Exception as e:
                st.warning(f"Erro ao calcular Key Level para {ticker}: {e}")

            # Condição Gamma (mantido igual)
            try:
                total_gex_sum = df_full['Gamma Exposure Total'].sum()
                condicao_gamma = "Neutra"
                if total_gex_sum > 0:
                    condicao_gamma = "Positiva"
                elif total_gex_sum < 0:
                    condicao_gamma = "Negativa"
            except Exception as e:
                condicao_gamma = "N/A"
                st.warning(f"Erro ao calcular Condição Gamma para {ticker}: {e}")

            # GEX 1-5 (mantido igual)
            gex_1 = None
            gex_2 = None
            gex_3 = None
            gex_4 = None
            gex_5 = None

            try:
                if not df_full.empty and exp_move_min is not None and exp_move_max is not None:
                    df_gex_intervalo = df_full[
                        (df_full['Strike'] >= exp_move_min) & (df_full['Strike'] <= exp_move_max)
                    ]
                    
                    if not df_gex_intervalo.empty:
                        df_gex_summary = df_gex_intervalo.groupby('Strike').agg(
                            TotalGammaSum=('Gamma Exposure Total', lambda x: x.abs().sum())
                        ).reset_index()

                        df_gex_summary = df_gex_summary.sort_values(by='TotalGammaSum', ascending=False)
                        
                        strikes_list = df_gex_summary['Strike'].tolist()
                        
                        if len(strikes_list) >= 1:
                            gex_1 = strikes_list[0]
                        if len(strikes_list) >= 2:
                            gex_2 = strikes_list[1]
                        if len(strikes_list) >= 3:
                            gex_3 = strikes_list[2]
                        if len(strikes_list) >= 4:
                            gex_4 = strikes_list[3]
                        if len(strikes_list) >= 5:
                            gex_5 = strikes_list[4]
                    else:
                        st.warning(f"Aviso para {ticker}: Nenhum strike encontrado dentro do intervalo de movimento esperado para as métricas GEX 1-5.")
            except Exception as e:
                st.warning(f"Erro ao calcular métricas GEX 1-5 para {ticker}: {e}")

            summary_metrics = {
                "1D Exp Move Min": exp_move_min,
                "1D Exp Move Max": exp_move_max,
                "Call Wall": call_wall,
                "Put Wall": put_wall,
                "Call Wall 0DTE": call_wall_0dte,
                "Put Wall 0DTE": put_wall_0dte,
                "Key Level": key_level,
                "Key Level 0DTE": key_level_0dte,
                "Condição Gamma": condicao_gamma,
                "GEX 1": gex_1,
                "GEX 2": gex_2,
                "GEX 3": gex_3,
                "GEX 4": gex_4,
                "GEX 5": gex_5
            }

            # --- Criação dos Filtros de Vencimento ---
            all_venc_filters = ["Todos os Vencimentos", "Todos os MENSAIS", "Todos os SEMANAIS"]
            
            vencimentos_individuais = df_full.drop_duplicates('VencimentoDT').sort_values('VencimentoDT')
            
            all_venc_filters.extend([f"{row['VencimentoDT'].strftime('%d/%m/%Y')} ({row['TipoVenc']})" for _, row in vencimentos_individuais.iterrows()])

            position_filters = ["Total", "Coberto", "Descoberto", "Travado"]

            # --- Processamento dos Dados para Gráficos (Data Store) ---
            data_store = {}
            for venc_filt in all_venc_filters:
                df_filt_venc = df_full.copy()
                if venc_filt == "Todos os Vencimentos":
                    df_filt_venc = df_full.copy()
                elif venc_filt == "Todos os MENSAIS":
                    df_filt_venc = df_full[df_full['TipoVenc'] == 'M'].copy()
                elif venc_filt == "Todos os SEMANAIS":
                    df_filt_venc = df_full[df_full['TipoVenc'] == 'W'].copy()
                else:
                    data_str = venc_filt.split(' ')[0]
                    df_filt_venc = df_full[df_full['VencimentoDT'].dt.strftime('%d/%m/%Y') == data_str].copy()
                
                if df_filt_venc.empty:
                    # Cria entradas vazias para filtros sem dados
                    for pos_filt in position_filters:
                        key = f"{venc_filt} - {pos_filt}"
                        data_store[key] = {
                            'gex_x': [], 'gex_y': [],
                            'gamma_call_y': [], 'gamma_put_y': [],
                            'oi_call_y': [], 'oi_put_y': [],
                            'skew_call_y': [], 'skew_put_y': [],
                            'strikes_gamma': [], 'strikes_oi': [],
                            'strikes_skew_call': [], 'strikes_skew_put': [],
                            'symbols': [], 'liquidity_text': [],
                            'symbols_call': [], 'liquidity_text_call': [],
                            'symbols_put': [], 'liquidity_text_put': []
                        }
                    continue

                for pos_filt in position_filters:
                    gamma_col = f'Gamma Exposure {pos_filt}'
                    oi_col = f'Open Interest {pos_filt}'

                    try:
                        # GEX (Total Gamma Exposure)
                        df_gex = df_filt_venc.groupby('Strike').agg(Total_Gamma=(gamma_col, 'sum')).reset_index()
                        
                        # Gamma Call vs Put
                        df_gamma_cp = df_filt_venc.pivot_table(index='Strike', columns='Tipo', values=gamma_col, aggfunc='sum').fillna(0)
                        
                        # Open Interest Call vs Put
                        df_oi_cp = df_filt_venc.pivot_table(index='Strike', columns='Tipo', values=oi_col, aggfunc='sum').fillna(0)
                        
                        # Skew de Volatilidade
                        df_skew = df_filt_venc[df_filt_venc['Volatilidade'] > 0].sort_values('Strike')
                        
                        # Customdata para hover: Símbolo e Liquidez. Corresponde ao Strike do df_gex
                        symbols_list = df_filt_venc.groupby('Strike')['symbol'].first().reindex(df_gex['Strike'], fill_value='N/A').tolist()
                        liquidity_text_list = df_filt_venc.groupby('Strike')['liquidity_text'].first().reindex(df_gex['Strike'], fill_value='N/A').tolist()
                        
                        key = f"{venc_filt} - {pos_filt}"
                        data_store[key] = {
                            'gex_x': df_gex['Strike'].tolist(), 'gex_y': (df_gex['Total_Gamma'] / 1_000_000).tolist(),
                            'gamma_call_y': (df_gamma_cp.get('CALL', 0) / 1_000_000).tolist(), 'gamma_put_y': (df_gamma_cp.get('PUT', 0) / 1_000_000).tolist(),
                            'oi_call_y': df_oi_cp.get('CALL', 0).tolist(), 'oi_put_y': df_oi_cp.get('PUT', 0).tolist(),
                            'skew_call_y': df_skew[df_skew['Tipo'] == 'CALL']['Volatilidade'].tolist(), 'skew_put_y': df_skew[df_skew['Tipo'] == 'PUT']['Volatilidade'].tolist(),
                            'strikes_gamma': df_gamma_cp.index.tolist(), 'strikes_oi': df_oi_cp.index.tolist(),
                            'strikes_skew_call': df_skew[df_skew['Tipo'] == 'CALL']['Strike'].tolist(), 'strikes_skew_put': df_skew[df_skew['Tipo'] == 'PUT']['Strike'].tolist(),
                            'symbols': symbols_list, 'liquidity_text': liquidity_text_list,
                            'symbols_call': df_skew[df_skew['Tipo'] == 'CALL']['symbol'].tolist(),
                            'liquidity_text_call': df_skew[df_skew['Tipo'] == 'CALL']['liquidity_text'].tolist(),
                            'symbols_put': df_skew[df_skew['Tipo'] == 'PUT']['symbol'].tolist(),
                            'liquidity_text_put': df_skew[df_skew['Tipo'] == 'PUT']['liquidity_text'].tolist()
                        }
                    except Exception as e:
                        st.error(f"Erro ao processar dados para {ticker} {venc_filt} - {pos_filt}: {e}")
                        traceback.print_exc()

            # --- Geração dos Gráficos ---
            figs = {}
            figs['gex_total'], figs['gex_desc'] = create_separate_charts('gex', all_venc_filters, data_store, spot_price)
            figs['gamma_cp_total'], figs['gamma_cp_desc'] = create_separate_charts('gamma_cp', all_venc_filters, data_store, spot_price)
            figs['oi_cp_total'], figs['oi_cp_desc'] = create_separate_charts('oi_cp', all_venc_filters, data_store, spot_price)
            figs['skew'] = create_single_chart_skew(all_venc_filters, data_store, spot_price)
            figs['gex_cumulativo_total'], figs['gex_cumulativo_desc'] = create_cumulative_gex_separate(all_venc_filters, df_full, spot_price)


            tickers_data[ticker] = {
                'summary_metrics': summary_metrics,
                'spot_price': spot_price,
                'figs': figs,
                'all_venc_filters': all_venc_filters
            }
            st.success(f"Processamento de {ticker} concluído.")

        except requests.RequestException as e:
            st.error(f"Erro ao buscar dados para {ticker}: {e}. Ticker ignorado.")
            continue
        except Exception as e:
            st.error(f"Erro inesperado no processamento de {ticker}: {e}")
            traceback.print_exc()
            continue

    if not tickers_data:
        st.error("Nenhum ticker processado com sucesso.")
        return None
    
    return tickers_data

def get_oplab_tickers():
    """Busca tickers na OpLab. Necessário para a primeira etapa de seleção."""
    try:
        url_oplab = "https://opcoes.oplab.com.br/mercado"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response_oplab = requests.get(url_oplab, headers=headers, timeout=10)
        response_oplab.raise_for_status()
        
        soup = BeautifulSoup(response_oplab.text, 'html.parser')
        ticker_elements = soup.find_all('p', class_='AssetCard_symbol__0AOFx')
        return sorted(list(set([ticker.text.strip() for ticker in ticker_elements if ticker.text.strip()])))
    except Exception as e:
        st.error(f"Erro ao buscar tickers da OpLab. Usando lista de tickers vazia. Erro: {e}")
        return []

# --- Renderização do Streamlit ---

def main():
    st.title("Gamma Exposure (GEX) e Volatilidade - Dashboard Multi Ticker")
    st.markdown("""
        Esta aplicação calcula e exibe métricas de **Gamma Exposure (GEX)**, **Open Interest (OI)** e **Volatilidade Implícita** para ativos do mercado brasileiro de opções.
    """)

    # --- Configuração de Entrada (Inputs) ---
    st.sidebar.header("Configurações de Entrada")
    
    # Busca os tickers disponíveis
    oplab_tickers = get_oplab_tickers()
    
    # Campo para data
    data_input = st.sidebar.text_input(
        "Digite a data de referência (YYYY-MM-DD)", 
        datetime.now().strftime('%Y-%m-%d')
    )
    
    try:
        data_formatada = datetime.strptime(data_input, '%Y-%m-%d')
        st.sidebar.success(f"Data selecionada: {data_formatada.strftime('%d/%m/%Y')}")
    except ValueError:
        st.sidebar.error("Formato de data inválido. Use YYYY-MM-DD.")
        return

    # Campo para entrada de Tickers
    all_tickers = oplab_tickers
    
    # Adicionar tickers manualmente
    manual_tickers_input = st.sidebar.text_input(
        "Adicionar tickers manualmente (separados por espaço, ex: PETR4 VALE3)",
        ""
    ).strip().upper()
    
    manual_tickers = [t.strip() for t in manual_tickers_input.split() if t.strip()]
    all_tickers = sorted(list(set(oplab_tickers + manual_tickers)))

    if not all_tickers:
        st.error("Nenhum ticker disponível ou fornecido. Verifique a conexão com a internet ou os tickers manuais.")
        return

    # Multi-seleção de tickers
    selected_tickers = st.sidebar.multiselect(
        "Selecione os tickers para processar:",
        options=all_tickers,
        default=oplab_tickers[:2] if oplab_tickers else all_tickers[:1]
    )

    if not selected_tickers:
        st.warning("Selecione pelo menos um ticker para processar.")
        return

    # Botão de processamento
    if st.sidebar.button("Processar Dados"):
        # Limpa o cache para forçar nova requisição, se a data mudar
        st.cache_data.clear()
        
        with st.spinner('Aguarde... Buscando e processando dados para os tickers selecionados.'):
            # Chamada da função que faz o trabalho pesado
            tickers_data = fetch_and_process_data(selected_tickers, data_formatada)
        
        if tickers_data:
            # Armazena os dados processados no estado da sessão para uso na UI
            st.session_state['tickers_data'] = tickers_data
            st.session_state['selected_ticker'] = selected_tickers[0] # Define o primeiro como padrão
            st.session_state['all_venc_filters'] = tickers_data[selected_tickers[0]]['all_venc_filters']

    # --- Renderização do Dashboard ---
    
    if 'tickers_data' in st.session_state and st.session_state['tickers_data']:
        tickers_data = st.session_state['tickers_data']
        
        # Seletor de Ticker
        st.header("Seletor de Ticker")
        current_ticker = st.selectbox(
            "Selecione o Ativo:",
            options=list(tickers_data.keys()),
            key='ticker_selector'
        )
        
        data = tickers_data[current_ticker]
        summary_metrics = data['summary_metrics']
        figs = data['figs']
        all_venc_filters = data['all_venc_filters']
        
        st.subheader(f"Métricas Chave para {current_ticker}")

        # --- Dashboard de Métricas (Melhorado com Streamlit) ---
        metric_labels = {
            "1D Exp Move Min": "Mov. Exp. Mínimo (1D)",
            "1D Exp Move Max": "Mov. Exp. Máximo (1D)",
            "Call Wall": "Call Wall (Todos)",
            "Put Wall": "Put Wall (Todos)",
            "Call Wall 0DTE": "Call Wall (0DTE)",
            "Put Wall 0DTE": "Put Wall (0DTE)",
            "Key Level": "Key Level (Todos)",
            "Key Level 0DTE": "Key Level (0DTE)",
            "Condição Gamma": "Condição Gamma",
            "GEX 1": "GEX 1 (Exp. Mv.)",
            "GEX 2": "GEX 2 (Exp. Mv.)",
            "GEX 3": "GEX 3 (Exp. Mv.)",
            "GEX 4": "GEX 4 (Exp. Mv.)",
            "GEX 5": "GEX 5 (Exp. Mv.)"
        }
        
# Layout de 3 colunas para as métricas
        cols = st.columns(3)
        i = 0
        copy_data_parts = [] # Lista para armazenar Label, Valor

        for key, label in metric_labels.items():
            value = summary_metrics[key]
            
            # 1. Valor para a métrica exibida no Dashboard (padrão BR: vírgula decimal)
            formatted_value_display = formatar_numero(value, 2) if isinstance(value, (float, int)) and value is not None else str(value) if value is not None else "N/A"
            
            # 2. Valor para a string de CÓPIA (padrão US: ponto decimal)
            if key == "Condição Gamma":
                # Condição Gamma é texto, não precisa de formatação numérica
                formatted_value_copy = str(value) if value is not None else "N/A"
            else:
                # Formata todos os valores numéricos (strikes e moves) para o padrão US (ponto decimal)
                formatted_value_copy = formatar_para_copia(value, 2)
            
            # Adiciona ao array de cópia no formato "Label, Valor"
            copy_data_parts.append(f"{label}, {formatted_value_copy}")
            
            # Renderiza a métrica no Streamlit com o valor formatado em BR
            cols[i % 3].metric(label=label, value=formatted_value_display)
            i += 1

        # --- Construção da String de Cópia ---
        # Junta todas as partes no formato: Label, Valor, Label, Valor...
        copy_text = ", ".join(copy_data_parts)

        # Exibe o texto para cópia
        st.code(copy_text, language='text')

        # Botão Copiar Métricas
        st.button("Copiar Métricas para a Área de Transferência", 
                  on_click=lambda: st.success("Texto copiado! (Esta função depende do navegador, use o botão nativo do Streamlit ao lado do bloco de código se não funcionar.)"))

        st.markdown("---")
        
        # --- Seletor de Vencimento para os Gráficos ---
        st.subheader("Visualização por Vencimento")
        vencimento_selector = st.selectbox(
            "Selecione o filtro de Vencimento para os gráficos:",
            options=all_venc_filters,
            key=f'venc_selector_{current_ticker}'
        )

        # --- Renderização dos Gráficos ---
        st.markdown("### Exposição Gamma (GEX)")
        col_gex_total, col_gex_desc = st.columns(2)
        
        # A lógica de visibilidade é tratada pelo Streamlit, basta renderizar
        if figs['gex_total']:
            with col_gex_total:
                # Atualiza a visibilidade do gráfico Total antes de renderizar
                fig_gex_total = update_chart_visibility(figs['gex_total'], all_venc_filters, vencimento_selector, is_dual_trace=False)
                st.plotly_chart(fig_gex_total, use_container_width=True, config={'displayModeBar': False})
        
        if figs['gex_desc']:
            with col_gex_desc:
                # Atualiza a visibilidade do gráfico Descoberto antes de renderizar
                fig_gex_desc = update_chart_visibility(figs['gex_desc'], all_venc_filters, vencimento_selector, is_dual_trace=False)
                st.plotly_chart(fig_gex_desc, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        
        st.markdown("### GEX Cumulativo (Fluxo de Pressão)")
        col_gex_cum_total, col_gex_cum_desc = st.columns(2)
        
        if figs['gex_cumulativo_total']:
            with col_gex_cum_total:
                fig_gex_cumulativo_total = update_chart_visibility(figs['gex_cumulativo_total'], all_venc_filters, vencimento_selector, is_dual_trace=False)
                st.plotly_chart(fig_gex_cumulativo_total, use_container_width=True, config={'displayModeBar': False})
        
        if figs['gex_cumulativo_desc']:
            with col_gex_cum_desc:
                fig_gex_cumulativo_desc = update_chart_visibility(figs['gex_cumulativo_desc'], all_venc_filters, vencimento_selector, is_dual_trace=False)
                st.plotly_chart(fig_gex_cumulativo_desc, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        
        st.markdown("### Exposição Gamma Call vs Put")
        col_gamma_cp_total, col_gamma_cp_desc = st.columns(2)
        
        if figs['gamma_cp_total']:
            with col_gamma_cp_total:
                fig_gamma_cp_total = update_chart_visibility(figs['gamma_cp_total'], all_venc_filters, vencimento_selector, is_dual_trace=True)
                st.plotly_chart(fig_gamma_cp_total, use_container_width=True, config={'displayModeBar': False})
        
        if figs['gamma_cp_desc']:
            with col_gamma_cp_desc:
                fig_gamma_cp_desc = update_chart_visibility(figs['gamma_cp_desc'], all_venc_filters, vencimento_selector, is_dual_trace=True)
                st.plotly_chart(fig_gamma_cp_desc, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        
        st.markdown("### Open Interest Call vs Put")
        col_oi_cp_total, col_oi_cp_desc = st.columns(2)
        
        if figs['oi_cp_total']:
            with col_oi_cp_total:
                fig_oi_cp_total = update_chart_visibility(figs['oi_cp_total'], all_venc_filters, vencimento_selector, is_dual_trace=True)
                st.plotly_chart(fig_oi_cp_total, use_container_width=True, config={'displayModeBar': False})
        
        if figs['oi_cp_desc']:
            with col_oi_cp_desc:
                fig_oi_cp_desc = update_chart_visibility(figs['oi_cp_desc'], all_venc_filters, vencimento_selector, is_dual_trace=True)
                st.plotly_chart(fig_oi_cp_desc, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("---")

        st.markdown("### Skew de Volatilidade Call vs Put")
        if figs['skew']:
            fig_skew = update_chart_visibility(figs['skew'], all_venc_filters, vencimento_selector, is_dual_trace=True)
            st.plotly_chart(fig_skew, use_container_width=True, config={'displayModeBar': False})
            
# Função auxiliar para atualizar a visibilidade dos traces no Streamlit
def update_chart_visibility(fig, all_venc_filters, current_venc, is_dual_trace):
    """Atualiza a propriedade 'visible' dos traces do Plotly com base no seletor de vencimento."""
    
    # Cria uma cópia da figura para modificação
    new_fig = go.Figure(fig)
    
    try:
        # Encontra o índice do vencimento atual
        venc_index = all_venc_filters.index(current_venc)
    except ValueError:
        # Fallback se o vencimento não for encontrado
        venc_index = 0

    num_traces = len(new_fig.data)
    num_filters = len(all_venc_filters)
    
    # Calcula o número de traces por filtro
    traces_per_filter = 2 if is_dual_trace else 1
    
    # Se o gráfico Skew estiver sendo processado, ele usa 2 traces por filtro
    if new_fig.layout.title.text.startswith("Skew de Volatilidade"):
        traces_per_filter = 2

    # A linha Spot Price e a linha Y=0 não contam para os índices de vencimento.
    # Elas são as últimas no array de dados do Plotly (se existirem).
    # O número de traces de vencimento é num_filters * traces_per_filter.
    
    # Cria o array de visibilidade
    visible = [False] * num_traces
    
    if is_dual_trace:
        # Para gráficos Call/Put e Skew (2 traces por vencimento)
        start_index = venc_index * 2
        
        if start_index < num_traces - (num_traces - num_filters * traces_per_filter): # Checa se o índice inicial é válido para traces de vencimento
            if start_index < len(new_fig.data):
                visible[start_index] = True     # Call/Trace 1
            if start_index + 1 < len(new_fig.data):
                visible[start_index + 1] = True # Put/Trace 2
    else:
        # Para gráficos GEX e GEX Cumulativo (1 trace por vencimento)
        start_index = venc_index * 1
        if start_index < num_traces - (num_traces - num_filters * traces_per_filter): # Checa se o índice inicial é válido para traces de vencimento
            if start_index < len(new_fig.data):
                visible[start_index] = True # GEX/Cumulativo

    # Garante que traces fixos (Spot Price e HLine) sejam visíveis
    num_venc_traces = num_filters * traces_per_filter
    for i in range(num_venc_traces, num_traces):
        visible[i] = True
        
    # Atualiza a propriedade 'visible' de cada trace
    for i, trace in enumerate(new_fig.data):
        new_fig.data[i].visible = visible[i]
        
    return new_fig

# Inicia a aplicação
if __name__ == '__main__':
    main()
