import pandas as pd

def get_attributes_for_area(
    plot_df,
    dataset_meta,
    attributes_meta,
    dataset_id,
    selected_area
):
    """
    Get all attributes for a selected area.

    Returns a list like:

    [
        {
            "attribute": "dist_water_m",
            "title": "Afstand tot water",
            "description": "...",
            "value": 1373,
            "unit": "m",
            "precision": 0
        },
        ...
    ]
    """

    if selected_area is None:
        return []

    area_rows = plot_df[
        plot_df[dataset_meta["key"]].astype(str)
        == str(selected_area)
    ]

    if area_rows.empty:
        return []

    row = area_rows.iloc[0]

    attributes = []

    for attribute_name, variants in attributes_meta.items():

        # Find metadata variant matching current dataset
        attribute_meta = next(
            (
                variant
                for variant in variants
                if variant["dataset"] == dataset_id
            ),
            None
        )

        if attribute_meta is None:
            continue

        # Attribute column must exist in dataframe
        if attribute_name not in row.index:
            continue

        attributes.append(
            {
                "attribute": attribute_name,
                "title": attribute_meta["title"],
                "description": attribute_meta["description"],
                "value": row[attribute_name],
                "unit": attribute_meta["unit"],
                "precision": attribute_meta["precision"],
            }
        )

    return attributes