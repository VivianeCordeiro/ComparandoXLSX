import streamlit as st

def upload_page():
    st.set_page_config(page_title="Comparador de Planilhas", layout="centered")
    st.title("📊 Comparador de Planilhas")
    st.header("🔁 Etapa 1: Envio dos Arquivos")
    st.markdown("Faça o upload de três arquivos `.xlsx`, `.xls` ou `.csv` para continuar.")

    # Inicializar variáveis no estado da sessão
    if "file1" not in st.session_state:
        st.session_state.file1 = None
    if "file2" not in st.session_state:
        st.session_state.file2 = None
    if "file3" not in st.session_state:
        st.session_state.file3 = None

    # Upload dos arquivos
    st.session_state.file1 = st.file_uploader(
        "📁 Primeiro arquivo (dados principais)", type=["xlsx", "xls", "csv"], key="file1_uploader"
    )
    st.session_state.file2 = st.file_uploader(
        "📁 Segundo arquivo (tabela de testes)", type=["xlsx", "xls", "csv"], key="file2_uploader"
    )
    st.session_state.file3 = st.file_uploader(
        "📁 Terceiro arquivo (tabela de alarmes)", type=["xlsx", "xls", "csv"], key="file3_uploader"
    )

    # Botão continuar
    if st.button("➡️ Continuar"):
        if st.session_state.file1 and st.session_state.file2 and st.session_state.file3:
            st.session_state.pagina = "opcoes"
        else:
            st.warning("🚨 Por favor, envie os três arquivos antes de continuar.")
