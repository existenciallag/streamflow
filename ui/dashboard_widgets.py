import pandas as pd


def general_reagents_quick_status(general_reagents, general_units):
    """
    Devuelve un resumen compacto del estado de reactivos generales
    pensado para dashboards tipo tablero (gauges / progress).

    Output columns:
    - Reactivo
    - In Use
    - Stored
    - Total
    - Ratio (In Use / Total)
    """

    # -----------------------------
    # Seguridad básica
    # -----------------------------
    if general_units is None or general_units.empty:
        return pd.DataFrame()

    if general_reagents is None or general_reagents.empty:
        return pd.DataFrame()

    # -----------------------------
    # Join unidades ↔ reactivo
    # -----------------------------
    df = general_units.merge(
        general_reagents[["id", "name"]],
        left_on="general_reagent_id",
        right_on="id",
        how="left"
    )

    # Por si hay unidades huérfanas
    df = df.dropna(subset=["name"])

    # -----------------------------
    # Conteo por estado
    # -----------------------------
    summary = (
        df.groupby("name")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )

    # -----------------------------
    # Normalizar estados esperados
    # -----------------------------
    for col in ["In Use", "Stored"]:
        if col not in summary.columns:
            summary[col] = 0

    # -----------------------------
    # Métricas útiles para dashboard
    # -----------------------------
    summary["Total"] = summary["In Use"] + summary["Stored"]

    summary["Ratio"] = (
        summary["In Use"] /
        summary["Total"].replace(0, 1)
    )

    # -----------------------------
    # Renombrado limpio
    # -----------------------------
    summary = summary.rename(columns={
        "name": "Reactivo"
    })

    # -----------------------------
    # Orden: primero lo más crítico
    # -----------------------------
    summary = summary.sort_values(
        by=["Ratio", "Total"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return summary
