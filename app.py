
import streamlit as st
from uploadPlanilha import upload_page
from analiseDados import analysis_page

if "pagina" not in st.session_state:
    st.session_state.pagina = "upload"

if st.session_state.pagina == "upload":
    upload_page()
elif st.session_state.pagina == "opcoes":
    analysis_page()
