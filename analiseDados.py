import streamlit as st
import pandas as pd
import time
import io
import re
import unicodedata


def _strip_accents(s: str) -> str:
    try:
        return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    except Exception:
        return s


def _norm_text(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    s = _strip_accents(s).upper()
    s = re.sub(r"\s+", "", s)          # remove espaços
    s = re.sub(r"[^A-Z0-9]", "", s)    # mantém só A–Z/0–9
    return s


def _norm_colname(cname: str) -> str:
    cname = _strip_accents(str(cname)).lower().strip()
    cname = cname.replace(":", "")
    cname = re.sub(r"\s+", " ", cname)
    return cname


def _find_col(df: pd.DataFrame, candidates) -> str | None:
    """Procura coluna por nomes normalizados exatos ou por 'contains'."""
    norm_map = {_norm_colname(c): c for c in df.columns}
    cand_norm = [_norm_colname(c) for c in candidates]
    # match exato
    for w in cand_norm:
        if w in norm_map:
            return norm_map[w]
    # match por contains
    for w in cand_norm:
        for k, orig in norm_map.items():
            if w in k:
                return orig
    return None


def _em_teste_is_true(v) -> bool | None:
    t = _strip_accents(str(v)).strip().upper()
    if t in {"SIM", "S", "YES", "Y", "TRUE", "1"}:
        return True
    if t in {"NAO", "NAO.", "N", "NAO ", "NAO*", "NAO/", "NAO-", "NAO_", "NÃO", "NO", "FALSE", "0"}:
        return False
    return None


def analysis_page():
    st.header("🛠️ Etapa 2: Análise de Dados")

    # file1 = principal; file2 = "Em Teste"; file3 = alarmes (opcional)
    if not (st.session_state.get("file1") and st.session_state.get("file2")):
        st.warning("Arquivos não carregados corretamente (é necessário ao menos arquivo 1 e 2).")
        return

    df1 = pd.read_excel(st.session_state.file1, header=2)
    df2 = pd.read_excel(st.session_state.file2, header=2)

    df3 = None
    if st.session_state.get("file3"):
        try:
            df3 = pd.read_excel(st.session_state.file3, header=2)
        except Exception:
            df3 = None  # fallback silencioso

    acao = st.selectbox(
        "Escolha uma ação:",
        ["Selecionar...", "Visualizar dados", "Procurar valores 'tm100'"]
    )

    if acao == "Visualizar dados":
        with st.spinner("Carregando dados..."):
            time.sleep(1)
            st.subheader("📄 Conteúdo do Arquivo 1")
            st.dataframe(df1)

            st.subheader("📄 Conteúdo do Arquivo 2 (Em Teste)")
            st.dataframe(df2)

            if df3 is not None:
                st.subheader("📄 Conteúdo do Arquivo 3 (Alarmes)")
                st.dataframe(df3)

    elif acao == "Procurar valores 'tm100'":
        # Checa colunas básicas
        if not all(c in df1.columns for c in ["Nome", "Valor", "Tipo"]):
            st.error("❌ As colunas 'Nome', 'Valor' e/ou 'Tipo' não foram encontradas no primeiro arquivo.")
            return

        # Detecta coluna de Número de Série na planilha 1
        col_ns_1 = _find_col(df1, [
            "Numero de Série", "Número de Série", "Numero de Serie", "Nº de Série", "N° de Série",
            "Numero de Serie:", "Serial", "Serial Number", "Num Serie", "NumeroSerie"
        ])

        # Detecta colunas na planilha 2 (Em Teste)
        col_ns_2 = _find_col(df2, [
            "Numero de Serie", "Número de Série", "Numero de Série", "Nº de Série", "N° de Série",
            "NumeroSerie", "Serial", "Serial Number"
        ])
        col_emteste = _find_col(df2, ["Em Teste", "Em Teste:", "EmTeste", "Em_Teste"])

        # Colunas da planilha 3 (Alarmes) - se não houver df3, usar df2 como fallback
        df_alarm = df3 if df3 is not None else df2.copy()
        col_placa_a = _find_col(df_alarm, ["Placa", "Placa:"])
        col_alarme  = _find_col(df_alarm, ["Alarme", "Alarme:"])

        if st.button("Iniciar análise"):
            # Valor → numérico
            df1["Valor"] = pd.to_numeric(
                df1["Valor"].astype(str).str.replace(",", ".", regex=False),
                errors="coerce"
            )
            # Tipo → minúsculas
            df1["Tipo"] = df1["Tipo"].astype(str).str.lower()

            # Saída
            df1["Análise de FEC"] = ""
            equipamentos_sem_gerencia = []

            # Dispositivos
            dispositivos = [
                "TM100","TM400","T100","TC100","TR100","T100DCT","T25DC","TCX12",
                "TM100G","T100-HA","TT100G","TF100G","TCX22-HA","TM100DCT","T100DC"
            ]

            # Regras por dispositivo (AND / OR)
            regras_tipo = {
                "TM400":      [["xfec 7%"], ["reed solomon"]],
                "T100":       ["fec", "taxa"],
                "TCX22-HA":   ["fec", "taxa"],
                "TC100":      ["fec", "taxa"],
                "TR100":      ["fec"],
                "T100DCT":    ["fec"],
                "T100DC":     ["fec"],
                "TM100DCT":   ["fec"],
                "T25DC":      ["nd"],
                "TCX12":      ["fec", "taxa"],
                "TM100G":     ["pré-fec"],
                "T100-HA":    [["xfec 7%"], ["reed solomon"]],
                "TT100G":     ["pré-fec"],
                "TF100G":     ["pré-fec"],
                "TM100":      ["pré-fec"],
            }

            limiares_tipo = {
                "XFEC/RS": 1e-4,     # XFEC 7% ou Reed Solomon
                "FEC_TAXA": 1e-6,    # FEC e TAXA
                "PRE_FEC": 1e-3,     # PRÉ FEC
            }

            alarmes_criticos = [
                "EQUIPAMENTO NAO RESPONDE",
                "EQUIPAMENTO NÃO RESPONDE",
                "TRAP DELL",
                "TEMPO DE RESPOSTA EXCEDIDO"
            ]

            def contem_todas(texto: str, palavras: list) -> bool:
                if pd.isna(texto):
                    return False
                t = str(texto).lower()
                return all(p.lower() in t for p in palavras)

            def tipo_combate_regra(tipo_texto: str, regra):
                if not regra:
                    return False
                if isinstance(regra, list) and regra and isinstance(regra[0], (list, tuple)):
                    return any(contem_todas(tipo_texto, sub) for sub in regra)
                else:
                    return contem_todas(tipo_texto, regra)

            # Pré-normaliza Número de Série em df1 e df2 (se existirem as colunas)
            if col_ns_1:
                df1["_SER_NORM_"] = df1[col_ns_1].apply(_norm_text)
            else:
                df1["_SER_NORM_"] = ""

            if col_ns_2:
                df2["_SER_NORM_"] = df2[col_ns_2].apply(_norm_text)

            def aplica_limiar(idx, dispositivo, tipo_lower, valor_float):
                if ("xfec 7%" in tipo_lower) or ("reed solomon" in tipo_lower):
                    limiar = limiares_tipo["XFEC/RS"]
                elif ("pré fec" in tipo_lower) or ("pre fec" in tipo_lower) or ("pré-fec" in tipo_lower) or ("pre-fec" in tipo_lower):
                    limiar = limiares_tipo["PRE_FEC"]
                elif ("fec" in tipo_lower and "taxa" in tipo_lower):
                    limiar = limiares_tipo["FEC_TAXA"]
                else:
                    return False
                df1.at[idx, "Análise de FEC"] = (
                    f"Recomendado para {dispositivo}" if valor_float < limiar
                    else f"Acima do recomendado para {dispositivo}"
                )
                return True

            # Loop por dispositivo
            for dispositivo in dispositivos:
                regra_tipo_disp = regras_tipo.get(dispositivo, [])

                # Evita que 'T100' case 'T100-HA' etc.
                padrao_nome = rf"{re.escape(dispositivo)}(?![-\w])"
                filtro_nome = df1["Nome"].astype(str).str.contains(padrao_nome, case=False, na=False, regex=True)

                # Tipo precisa obedecer às regras
                filtro_tipo = df1["Tipo"].apply(lambda x: tipo_combate_regra(x, regra_tipo_disp))

                filtro_total = filtro_nome & filtro_tipo

                for idx in df1[filtro_total].index:
                    nome_dispositivo = str(df1.at[idx, "Nome"])
                    tipo_lower = str(df1.at[idx, "Tipo"]).lower()
                    valor = df1.at[idx, "Valor"]

                    if pd.isna(valor):
                        continue
                    try:
                        valor_float = float(valor)
                    except (TypeError, ValueError):
                        continue

                    # extrai número após '#'
                    m = re.search(r"#\s*(\d+)", nome_dispositivo)
                    numero = m.group(1) if m else None

                    if valor_float == 0.0:
                        # 1) Verifica Em Teste
                        if col_ns_2 and col_emteste and col_ns_1:
                            ser_norm_1 = df1.at[idx, "_SER_NORM_"]
                            linhas_t = df2[df2["_SER_NORM_"] == ser_norm_1] if ser_norm_1 else pd.DataFrame(columns=df2.columns)
                            if not linhas_t.empty:
                                emteste_vals = linhas_t[col_emteste].fillna("").astype(str).apply(_em_teste_is_true)
                                if True in set(emteste_vals):
                                    df1.at[idx, "Análise de FEC"] = "Placa em teste"
                                    continue

                        # 2) Verifica Alarmes
                        if col_placa_a and col_alarme:
                            if numero:
                                padrao_df3 = rf"{re.escape(dispositivo)}(?![-\w]).*#\s*{numero}(?!\d)"
                            else:
                                padrao_df3 = rf"{re.escape(dispositivo)}(?![-\w])"

                            candidatos_a = df_alarm[col_placa_a].astype(str).str.contains(
                                padrao_df3, case=False, na=False, regex=True
                            )
                            linhas_a = df_alarm[candidatos_a]

                            if not linhas_a.empty:
                                alarmes_txt = linhas_a[col_alarme].fillna("").astype(str)
                                up = alarmes_txt.str.upper()
                                criticos_encontrados = [a for a in alarmes_criticos if up.str.contains(a, regex=False).any()]
                                if criticos_encontrados:
                                    equipamentos_sem_gerencia.append({
                                        **df1.loc[idx].to_dict(),
                                        "Alarme encontrado": criticos_encontrados[0]
                                    })
                                    continue

                        # 3) Aplica limiar
                        if aplica_limiar(idx, dispositivo, tipo_lower, valor_float):
                            continue
                        else:
                            continue

                    aplica_limiar(idx, dispositivo, tipo_lower, valor_float)

            # Filtra resultados
            resultados = df1[df1["Análise de FEC"].notna() & (df1["Análise de FEC"] != "")]
            df_sem_gerencia = pd.DataFrame(equipamentos_sem_gerencia)

            st.subheader("🔍 Dispositivos com ações recomendadas")

            if resultados.empty and df_sem_gerencia.empty:
                st.info("ℹ️ Nenhuma ocorrência válida foi encontrada conforme os critérios.")
            else:
                if "_SER_NORM_" in resultados.columns:
                    resultados = resultados.drop(columns=["_SER_NORM_"])
                if "_SER_NORM_" in df_sem_gerencia.columns:
                    df_sem_gerencia = df_sem_gerencia.drop(columns=["_SER_NORM_"])

                resultados = resultados.dropna(axis=1, how='all')
                resultados = resultados.loc[:, (resultados != '').any(axis=0)]
                df_sem_gerencia = df_sem_gerencia.dropna(axis=1, how='all')
                df_sem_gerencia = df_sem_gerencia.loc[:, (df_sem_gerencia != '').any(axis=0)]

                # Salvar em um Excel com duas abas
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    resultados.to_excel(writer, sheet_name="Analise FEC", index=False)
                    if not df_sem_gerencia.empty:
                        df_sem_gerencia.to_excel(writer, sheet_name="Equipamentos sem gerencia", index=False)

                buffer.seek(0)
                st.download_button(
                    label="📥 Baixar planilha com abas",
                    data=buffer,
                    file_name="planilha_analise_com_abas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "upload"
