import streamlit as st
st.set_page_config(page_title="Comparador de Planilhas", layout="centered")

def upload_page():
    st.title("📊 Comparador de Planilhas")
    st.header("🔁 Etapa 1: Envio dos Arquivos")
    st.markdown("Faça o upload de arquivos `.xlsx`, `.xls` ou `.csv` para continuar.")

    # Inicializa variáveis
    st.session_state.setdefault("file1", None)
    st.session_state.setdefault("file2", None)
    st.session_state.setdefault("file3", None)
    st.session_state.setdefault("file4", None)

    # FORM evita múltiplos reruns – clique único
    with st.form("upload_form", clear_on_submit=False):
        file1_local = st.file_uploader("📁 Dados das Medidas", type=["xlsx", "xls", "csv"], key="file1_uploader")
        file2_local = st.file_uploader("📁 Dados de Placas", type=["xlsx", "xls", "csv"], key="file2_uploader")
        file3_local = st.file_uploader("📁 Dados de Alarmes", type=["xlsx", "xls", "csv"], key="file3_uploader")
        file4_local = st.file_uploader("📁 Dados de Alarmes Supervisores", type=["xlsx", "xls", "csv"], key="file4_uploader")

        submit = st.form_submit_button("➡️ Continuar")

    # ---- AQUI FORA DO FORM ----
    if submit:
        # salva apenas o que foi enviado nesta submissão
        if file1_local: st.session_state.file1 = file1_local
        if file2_local: st.session_state.file2 = file2_local
        if file3_local: st.session_state.file3 = file3_local
        if file4_local: st.session_state.file4 = file4_local

        # validação
        if st.session_state.file1 and st.session_state.file2:
            st.session_state.pagina = "opcoes"
            st.rerun()  # rerun correto
        else:
            st.warning("🚨 Por favor, envie pelo menos os arquivos 1 e 2 antes de continuar.")
