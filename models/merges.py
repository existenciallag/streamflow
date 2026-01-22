import pandas as pd

def build_inventory(
    reagents,
    general_reagents,
    brands,
    fluoros,
    units,
    general_units
):
    # ============================================================
    # 1) ANTICUERPOS
    # ============================================================
    reagents_merged = (
        reagents
        .merge(
            brands.add_suffix("_brand"),
            left_on="brand_id",
            right_on="id_brand",
            how="left"
        )
        .merge(
            fluoros.add_suffix("_fluor"),
            left_on="fluorochrome",
            right_on="id_fluor",
            how="left"
        )
    )

    inventory_specific = units.merge(
        reagents_merged,
        left_on="reagent_id",
        right_on="id",
        how="left"
    )
    inventory_specific["item_type"] = "antibody"

    # ============================================================
    # 2) REACTIVOS GENERALES
    # ============================================================
    general_merged = (
        general_reagents
        .merge(
            brands.add_suffix("_brand"),
            left_on="brand_id",
            right_on="id_brand",
            how="left"
        )
    )

    inventory_general = general_units.merge(
        general_merged,
        left_on="general_reagent_id",
        right_on="id",
        how="left"
    )
    inventory_general["item_type"] = "general_reagent"

    # ============================================================
    # 3) UNIFICACIÓN TOTAL
    # ============================================================
    inv = pd.concat(
        [inventory_specific, inventory_general],
        ignore_index=True,
        sort=False
    )

    # ============================================================
    # 4) NORMALIZAR FECHAS
    # ============================================================
    date_cols = [
        "expiration_date",
        "arrival_date",
        "created_at",
        "updated_at",
        "preparation_date"
    ]

    for col in date_cols:
        if col in inv.columns:
            inv[col] = pd.to_datetime(inv[col], errors="coerce")

    # ============================================================
    # 5) CREAR ID ÚNICO PARA INVENTARIO
    # ============================================================
    inv.insert(0, "id", inv.index.astype(int))

    return inv
