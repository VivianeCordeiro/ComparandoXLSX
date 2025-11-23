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
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9()]", "", s)
    return s

def _norm_colname(cname: str) -> str:
    cname = _strip_accents(str(cname)).lower().strip()
    cname = cname.replace(":", "")
    cname = re.sub(r"\s+", " ", cname)
    return cname

def _find_col(df: pd.DataFrame, candidates) -> str | None:
    norm_map = {_norm_colname(c): c for c in df.columns}
    cand_norm = [_norm_colname(c) for c in candidates]
    for w in cand_norm:
        if w in norm_map:
            return norm_map[w]
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
    st.title("📈 Análise das Planilhas")

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
            df3 = None

    df4 = None
    if st.session_state.get("file4"):
        try:
            df4 = pd.read_excel(st.session_state.file4, header=2)
        except Exception:
            df4 = None

    acao = st.selectbox(
        "Escolha uma ação:",
        ["Selecionar...", "Visualizar dados", "Analisar dados"]
    )

    if acao == "Visualizar dados":
        with st.spinner("Carregando dados..."):
            time.sleep(1)
            st.subheader("📄 Conteúdo do Arquivo 1")
            st.dataframe(df1)

            st.subheader("📄 Conteúdo do Arquivo 2")
            st.dataframe(df2)

            if df3 is not None:
                st.subheader("📄 Conteúdo do Arquivo 3")
                st.dataframe(df3)
            if df4 is not None:
                st.subheader("📄 Conteúdo do Arquivo 4")
                st.dataframe(df4)

    elif acao == "Analisar dados":
        # validações iniciais
        if not all(c in df1.columns for c in ["Nome", "Valor", "Tipo"]):
            st.error("❌ As colunas 'Nome', 'Valor' e/ou 'Tipo' não foram encontradas no primeiro arquivo.")
            return

        col_ns_1 = _find_col(df1, [
            "Numero de Série", "Número de Série", "Numero de Serie", "Nº de Série", "N° de Série",
            "Numero de Serie:", "Serial", "Serial Number", "Num Serie", "NumeroSerie"
        ])
        col_ns_2 = _find_col(df2, [
            "Numero de Serie", "Número de Série", "Numero de Série", "Nº de Série", "N° de Série",
            "NumeroSerie", "Serial", "Serial Number"
        ])
        col_emteste = _find_col(df2, ["Em Teste", "Em Teste:", "EmTeste", "Em_Teste"])

        df_alarm = df3 if df3 is not None else df2.copy()
        col_placa_a = _find_col(df_alarm, ["Placa", "Placa:"])
        col_alarme = _find_col(df_alarm, ["Alarme", "Alarme:"])

        if st.button("Iniciar análise"):
            # normalizações iniciais
            df1["Valor"] = pd.to_numeric(
                df1["Valor"].astype(str).str.replace(",", ".", regex=False),
                errors="coerce"
            )
            df1["Tipo"] = df1["Tipo"].astype(str).str.lower()
            df1["Análise de FEC"] = ""
            equipamentos_sem_gerencia = []
            placas_em_teste = []

            # ========================
            # device detection (prioridade e regex robustos)
            # ========================
            device_patterns = [
                ("T100DCT",   r"(?<![A-Z0-9])T100DCT(?=[^A-Z]|$)"),
                ("T100DC",    r"(?<![A-Z0-9])T100DC(?=[^A-Z]|$)"),
                ("T100",      r"(?<![A-Z0-9])T100(?!D|DC|DCT)(?=[^A-Z]|$)"),

                ("TM100G",    r"(?<![A-Z0-9])TM100G(?![A-Z])"),
                ("TM100",     r"(?<![A-Z0-9])TM100(?!G)(?=[^A-Z]|$)"),
                ("TM400",     r"(?<![A-Z0-9])TM400(?=[^A-Z]|$)"),

                ("TCX22-HA",  r"(?<![A-Z0-9])TCX22-HA(?=[^A-Z]|$)"),
                ("TCX22",     r"(?<![A-Z0-9])TCX22(?=[^A-Z]|$)"),
                ("TCX12",     r"(?<![A-Z0-9])TCX12(?=[^A-Z]|$)"),
                ("TC100",     r"(?<![A-Z0-9])TC100(?=[^A-Z]|$)"),

                ("T25DC",     r"(?<![A-Z0-9])T25DC(?=[^A-Z]|$)"),
                ("TR100",     r"(?<![A-Z0-9])TR100(?=[^A-Z]|$)"),
                ("TT100G",    r"(?<![A-Z0-9])TT100G(?=[^A-Z]|$)"),
                ("TF100G",    r"(?<![A-Z0-9])TF100G(?=[^A-Z]|$)"),
            ]
            
            def identificar_dispositivo(nome):
                nome_limpo = str(nome).upper()
                for dispositivo, pat in device_patterns:
                    m = re.search(pat, nome_limpo)
                    if m:
                        return dispositivo, m.group()
                return None, None

            # cria colunas auxiliares com o device detectado
            df1["_DETECTED_DEVICE_"], df1["_DETECTED_RAW_"] = zip(
                *df1["Nome"].astype(str).apply(lambda x: identificar_dispositivo(x))
            )

            # ========================
            # regras e limiares (mantendo sua lógica)
            # ========================
            regras_tipo = {
                "TM400": [["xfec 7%"], ["reed solomon"]],
                "T100": ["fec", "taxa"],
                "TCX22-HA": ["fec", "taxa"],
                "TC100": ["fec", "taxa"],
                "TR100": ["fec"],
                "T100DCT": ["fec"],
                "T100DC": ["fec"],
                "TM100DCT": ["fec"],
                "T25DC": ["nd"],
                "TCX12": ["fec", "taxa"],
                "TM100G": ["pré-fec"],
                "T100-HA": [["xfec 7%"], ["reed solomon"]],
                "TT100G": ["pré-fec"],
                "TF100G": ["pré-fec"],
                "TM100": ["pré-fec"],
            }

            limiares_tipo = {
                "XFEC/RS": 1e-4,
                "FEC_TAXA": 1e-6,
                "PRE_FEC": 1e-3,
            }

            alarmes_criticos = [
                "EQUIPAMENTO NAO RESPONDE",
                "EQUIPAMENTO NÃO RESPONDE",
                "TRAP DELL",
                "TEMPO DE RESPOSTA EXCEDIDO"
            ]
            colunas_remover = [
                "_SER_NORM_",
                "_DETECTED_DEVICE_",
                "_DETECTED_RAW_"
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

            # criar coluna de serial normalizado (se aplicável)
            if col_ns_1:
                df1["_SER_NORM_"] = df1[col_ns_1].apply(_norm_text)
            else:
                df1["_SER_NORM_"] = ""

            if col_ns_2:
                df2["_SER_NORM_"] = df2[col_ns_2].apply(_norm_text)

            # função de aplicar limiar (mantida mas recebe dispositivo/tipo)
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

            # ================
            # Loop por linha (cada linha tem no máximo 1 dispositivo detectado)
            # ================
            for idx in df1.index:
                dispositivo = df1.at[idx, "_DETECTED_DEVICE_"]
                if not dispositivo:
                    continue  # pula linhas sem dispositivo detectado

                regra_tipo_disp = regras_tipo.get(dispositivo, [])
                tipo_lower = str(df1.at[idx, "Tipo"]).lower()
                valor = df1.at[idx, "Valor"]

                # valida tipo do dispositivo (mesma lógica anterior)
                if not tipo_combate_regra(tipo_lower, regra_tipo_disp):
                    continue

                # valida valor
                if pd.isna(valor):
                    continue
                try:
                    valor_float = float(valor)
                except (TypeError, ValueError):
                    continue

                nome_dispositivo = str(df1.at[idx, "Nome"])

                # extrai número após "#" se houver
                m = re.search(r"#\s*(\d+)", nome_dispositivo)
                numero = m.group(1) if m else None

                # se valor == 0 verifica placa em teste e alarms
                if valor_float == 0.0:
                    # verifica se placa está em teste (usa df2 com serial normalizado)
                    if col_ns_2 and col_emteste and col_ns_1:
                        ser_norm_1 = df1.at[idx, "_SER_NORM_"]
                        linhas_t = df2[df2["_SER_NORM_"] == ser_norm_1] if ser_norm_1 else pd.DataFrame(columns=df2.columns)
                        if not linhas_t.empty:
                            emteste_vals = linhas_t[col_emteste].fillna("").astype(str).apply(_em_teste_is_true)
                            if True in set(emteste_vals):
                                df1.at[idx, "Análise de FEC"] = "Placa em teste"
                                placas_em_teste.append(df1.loc[idx].to_dict())
                                df1 = df1.drop(idx)
                                continue

                    # procura alarmes críticos no df_alarm (df3 se disponível ou df2)
                    if col_placa_a and col_alarme:
                        # busca a placa no df_alarm de forma permissiva (dispositivo + ... #numero)
                        if numero:
                            padrao_df3 = rf"{re.escape(dispositivo)}.*#\s*{numero}"
                        else:
                            padrao_df3 = rf"{re.escape(dispositivo)}"

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

                    # se nenhum caso acima, tenta aplicar limiar (pode falhar se tipo não bater com padrões do limiar)
                    if aplica_limiar(idx, dispositivo, tipo_lower, valor_float):
                        continue
                    else:
                        continue

                # se valor != 0 aplica limiar normalmente
                aplica_limiar(idx, dispositivo, tipo_lower, valor_float)

            # montagem dos resultados finais
            resultados = df1[df1["Análise de FEC"].notna() & (df1["Análise de FEC"] != "")]
            df_sem_gerencia = pd.DataFrame(equipamentos_sem_gerencia)
            df_placas_em_teste = pd.DataFrame(placas_em_teste)

            # analise para supervisores (arquivo df4)
            analise_supervisores = []
            if df4 is not None:
                col_placa_df4 = _find_col(df4, ["Placa", "Placa:"])
                col_alarme_df4 = _find_col(df4, ["Alarme", "Alarme:"])
                col_ne_df4 = _find_col(df4, ["NE", "NE:"])

                placas_alvo = ["SPVL-4", "SPVL-91", "SPVL-HB", "SPVL-90"]
                alarmes_site_sem_ger = [
                    "TEMPO DE RESPOSTA EXCEDIDO (RESYNC)",
                    "EQUIPAMENTO NAO RESPONDE (TRAP DEL",
                    "EQUIPAMENTO NAO RESPONDE (HISTORY LAST_ALARMS)",
                    "TEMPO DE RESPOSTA EXCEDIDO (SC)",
                    "TEMPO DE RESPOSTA EXCEDIDO (DCN)"
                ]
                alarmes_dcn = [
                    "DCN LINK DOWN",
                    "FALHA DE COMUNICACAO (CONNECTION TIMED OUT)",
                    "FALHA DE COMUNICACAO (NO ROUTE TO HOST (HOST UNREACHABLE))",
                    "FALHA DE COMUNICACAO (CONNECTION REFUSED)"
                ]

                for _, row in df4.iterrows():
                    placa_orig = str(row.get(col_placa_df4, ""))   # mantém formato original
                    alarme_norm = _norm_text(str(row.get(col_alarme_df4, "")))  # só para comparação
                    ne_orig = row.get(col_ne_df4, "")              # mantém formato original

                    if any(_norm_text(p) in _norm_text(placa_orig) for p in placas_alvo):
                        if any(_norm_text(a) in alarme_norm for a in alarmes_site_sem_ger):
                            analise_supervisores.append({
                                "NE": ne_orig,           # mantém original
                                "Placa:": placa_orig,    # mantém original
                                "Análise": "Site sem gerenciamento, necessário verificar supervisor."
                            })
                        elif any(_norm_text(a) in alarme_norm for a in alarmes_dcn):
                            analise_supervisores.append({
                                "NE": ne_orig,           # mantém original
                                "Placa:": placa_orig,    # mantém original
                                "Análise": "Falha de Comunicacao, necessário verificar a conexão da placa com a rede DCN"
                            })

            df_analise_supervisores = pd.DataFrame(analise_supervisores)

            # resultado final e export
            st.subheader("🔍 Dispositivos com ações recomendadas")

            if resultados.empty and df_sem_gerencia.empty and df_analise_supervisores.empty:
                st.info("ℹ️ Nenhuma ocorrência válida foi encontrada conforme os critérios.")
            else:
                # Remove colunas nos dois dataframes, ignorando as que não existirem
                resultados = resultados.drop(columns=colunas_remover, errors='ignore')
                df_sem_gerencia = df_sem_gerencia.drop(columns=colunas_remover, errors='ignore')

                # limpa colunas vazias
                resultados = resultados.dropna(axis=1, how='all')
                resultados = resultados.loc[:, (resultados != '').any(axis=0)]
                df_sem_gerencia = df_sem_gerencia.dropna(axis=1, how='all')
                df_sem_gerencia = df_sem_gerencia.loc[:, (df_sem_gerencia != '').any(axis=0)]
                # Criar DF apenas com placas em teste
                df_placas_em_teste = pd.DataFrame(placas_em_teste)
                df_placas_em_teste = df_placas_em_teste.dropna(axis=1, how='all')
                df_placas_em_teste = df_placas_em_teste.drop(columns=colunas_remover, errors='ignore')

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    resultados.to_excel(writer, sheet_name="Análise FEC", index=False)
                    if not df_placas_em_teste.empty:
                        df_placas_em_teste.to_excel(writer, sheet_name="Placas em teste", index=False)
                    if not df_sem_gerencia.empty:
                        df_sem_gerencia.to_excel(writer, sheet_name="Equipamentos sem gerência", index=False)
                    if not df_analise_supervisores.empty:
                        df_analise_supervisores.to_excel(writer, sheet_name="Alarmes Supervisores", index=False)
                    
                buffer.seek(0)
                st.download_button(
                    label="📥 Download da análise",
                    data=buffer,
                    file_name="analise_equipamentos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        if st.button("⬅️ Voltar"):
            st.session_state.pagina = "upload"
            st.rerun()
