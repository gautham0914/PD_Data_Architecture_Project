import re

DISALLOWED = {
    "insert","update","delete","drop","alter","create","truncate","grant","revoke",
    "copy","call","do","execute"
}

VIEW_PREFIX = "pd.v_"


def enforce_readonly(sql: str, default_limit: int = 200) -> str:
    """Validate and rewrite SQL safely.
    Rules:
    - Single statement only (allow one trailing semicolon)
    - Must be SELECT or WITH ... SELECT
    - Reject dangerous keywords
    - Block information_schema, pg_catalog, pg_*
    - Require FROM/JOIN only on pd.v_* views
    - If LIMIT missing, append LIMIT {default_limit}
    """
    s = (sql or "").strip()
    # Single statement
    semicolons = [m.start() for m in re.finditer(r";", s)]
    if len(semicolons) > 1:
        raise ValueError("Multiple statements are not allowed.")

    # Must be SELECT or WITH ... SELECT
    if not re.match(r"^(\s*with\b.*select\b|\s*select\b)", s, re.IGNORECASE | re.DOTALL):
        raise ValueError("Only SELECT (or WITH ... SELECT) statements are permitted.")

    # Disallow dangerous keywords
    if re.search(r"\b(" + "|".join(DISALLOWED) + r")\b", s, re.IGNORECASE):
        raise ValueError("Statement contains disallowed keywords.")

    # Block system schemas
    if re.search(r"\binformation_schema\b|\bpg_catalog\b|\bpg_\w+\b", s, re.IGNORECASE):
        raise ValueError("Access to system schemas is blocked.")

    # Validate FROM/JOIN identifiers
    identifiers = re.findall(r"\b(?:from|join)\s+([a-zA-Z0-9_.\"]+)", s, re.IGNORECASE)
    if not identifiers:
        raise ValueError("Query must reference at least one view.")
    for ident in identifiers:
        ident_clean = ident.replace('"','')
        if not ident_clean.startswith(VIEW_PREFIX):
            raise ValueError("Queries must use read-only views named pd.v_* only.")

    # Append LIMIT if missing
    if not re.search(r"\blimit\b", s, re.IGNORECASE):
        s = s.rstrip("; ") + f"\nlimit {default_limit};"
    return s
