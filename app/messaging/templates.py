def build_missing_docs_message(client_name: str, missing_docs: list[str]) -> str:
    docs = ", ".join(missing_docs) if missing_docs else "ninguno"
    return (
        f"Hola {client_name}, para tramitar tu renovacion necesitamos: {docs}. "
        "Cuando los tengas, responde a este mensaje."
    )
