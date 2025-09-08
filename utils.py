import pandas as pd

def carregar_arquivo(arquivo, header_linha=0):
    if arquivo is None:
        return None
    if arquivo.name.endswith(".xlsx") or arquivo.name.endswith(".xls"):
        return pd.read_excel(arquivo, header=header_linha)
    elif arquivo.name.endswith(".csv"):
        return pd.read_csv(arquivo, header=header_linha, sep=None, engine="python")
    else:
        raise ValueError("Tipo de arquivo não suportado.")
