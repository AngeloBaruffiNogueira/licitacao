import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import re

@st.cache_data
def load_data():
    """Loads the bidding dataset from the pickle file and caches it."""
    data_path = os.path.join(os.path.dirname(__file__), "contracts_clean.pkl")
    return pd.read_pickle(data_path)

# --- Page Configuration ---
st.set_page_config(page_title="Painel de Licitações", layout="wide")

# --- State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_filters" not in st.session_state:
    st.session_state.show_filters = False
if "show_columns" not in st.session_state:
    st.session_state.show_columns = False
if "selected_columns" not in st.session_state:
    st.session_state.selected_columns = [
        "numeroControlePNCP",
        "dataAberturaProposta",
        "dataEncerramentoProposta",
        "objetoCompra",
        "valor",
        "situacaoCompraNome",
        "tipoIntrumentoConvocatorioNome",
        "poder"
    ]

# --- User Authentication ---
def login_page():
    """Displays the login page and handles authentication."""
    st.title("Acesso")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if username == "Renato" and password == "12345678":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

# --- Excel Export ---
def to_excel(df: pd.DataFrame):
    """Converts a DataFrame to an Excel file in memory, removing characters illegal in Excel worksheets."""
    # Regex pattern mirrors openpyxl's illegal character set: 0x00‑0x08, 0x0B, 0x0C, 0x0E‑0x1F
    illegal_char_re = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

    def _clean_value(x):
        if isinstance(x, str):
            return illegal_char_re.sub("", x)
        return x

    df_clean = df.applymap(_clean_value)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Biddings')
    return output.getvalue()

def add_pncp_links(df: pd.DataFrame) -> pd.DataFrame:
    """
    (Placeholder for possible link-adder. Not implemented.)
    """
    return df

# --- Helper: Parse multiple keywords ---
# --- Helper: Parse multiple keywords ---
def parse_keywords(text: str) -> list[str]:
    """
    Split the text by semicolons (;) to support multiple keywords/phrases.
    Strips whitespace and discards empty tokens.
    """
    if not text:
        return []
    return [token.strip() for token in text.split(';') if token.strip()]

# --- Main App Interface ---
def main_interface():
    """Displays the main application interface after successful login."""
    df_full = load_data()
    st.title("Bem-vindo ao Portal de Licitações, Renato!")

    # # --- Company Description Textarea ---
    # st.write("##### Por favor, descreva sua empresa: quem vocês são, o que fazem e o que estão procurando.")
    # st.text_area("Descrição da Empresa", height=150, label_visibility="collapsed", placeholder="Insira a descrição da sua empresa aqui...")

    # --- Columns Section ---
    if st.button("Colunas"):
        st.session_state.show_columns = not st.session_state.show_columns

    if st.session_state.show_columns:
        with st.container(border=True):
            available_columns = list(df_full.columns)
            # Keep only defaults that actually exist in the dataset
            default_cols = [
                col for col in st.session_state.selected_columns
                if col in available_columns
            ]
            # Fallback: if none of the desired defaults exist, use the first five columns
            if not default_cols and available_columns:
                default_cols = available_columns[:5]

            st.session_state.selected_columns = st.multiselect(
                "Selecione as colunas para exibir",
                options=available_columns,
                default=default_cols,
            )

    # --- Filters Section ---
    if st.button("Filtros"):
        st.session_state.show_filters = not st.session_state.show_filters

    if st.session_state.show_filters:
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.session_state["status_filter"] = st.multiselect(
                    "Situação",
                    options=sorted(df_full['situacaoCompraNome'].dropna().unique()),
                )
                st.session_state["uf_filter"] = st.multiselect(
                    "Estado (UF)",
                    options=sorted(df_full['ufSigla'].dropna().unique()),
                )
            with col2:
                st.session_state["city_filter"] = st.multiselect(
                    "Município",
                    options=sorted(df_full['municipioNome'].dropna().unique()),
                )
                st.session_state["type_filter"] = st.multiselect(
                    "Modalidade",
                    options=sorted(df_full['modalidadeNome'].dropna().unique()),
                )
            with col3:
                st.session_state["min_value"] = st.number_input("Valor mínimo da licitação", min_value=0, step=1000)

    # --- Search Bar ---
    keyword = st.text_input(
        "Pesquisar por palavra‑chave ou frase (use ponto e vírgula “;” para múltiplos termos – busca OR)",
        placeholder="Ex.: medicamento; material hospitalar",
    )

    if st.button("Buscar"):
        df = df_full.copy()

        # Apply filters if they exist
        status_filter = st.session_state.get("status_filter", [])
        uf_filter = st.session_state.get("uf_filter", [])
        city_filter = st.session_state.get("city_filter", [])
        type_filter = st.session_state.get("type_filter", [])
        min_value = st.session_state.get("min_value", 0)

        if status_filter:
            df = df[df['situacaoCompraNome'].isin(status_filter)]
        if uf_filter:
            df = df[df['ufSigla'].isin(uf_filter)]
        if city_filter:
            df = df[df['municipioNome'].isin(city_filter)]
        if type_filter:
            df = df[df['modalidadeNome'].isin(type_filter)]
        if min_value:
            df = df[df['valor'] >= min_value]

        keywords = parse_keywords(keyword)
        if keywords:
            # Build an OR regex pattern with the escaped keywords/phrases
            pattern = "|".join(re.escape(term) for term in keywords)
            df = df[df['objetoCompra'].str.contains(pattern, case=False, na=False, regex=True)]

        # --- Column Re‑ordering & Selection ---
        display_columns = [
            col for col in st.session_state.get("selected_columns", [])
            if col in df.columns
        ]
        if not display_columns:
            display_columns = list(df.columns)  # fallback to all columns
        df_display = df[display_columns]

        # --- KPIs ---
        num_rows = len(df)
        total_valor = df['valor'].sum()
        valor_total_display = f"R$ {total_valor:,.2f}"

        col_kpi1, col_kpi2 = st.columns(2)
        col_kpi1.metric("Total de Registros", num_rows)
        col_kpi2.metric("Valor Total", valor_total_display)

        st.write("### Oportunidades de Licitação")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        if not df.empty:
            excel_data = to_excel(df_display)
            st.download_button(
                label="📥 Exportar para Excel",
                data=excel_data,
                file_name="bidding_opportunities.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download-excel'
            )

# --- App Execution ---
if st.session_state.logged_in:
    main_interface()
else:
    login_page()