"""
Module for building table visualizations for datasets with multiple indicators.
Used when visualization_type is set to "table" in metadata.
"""

import pandas as pd
from streamlit.logger import get_logger

logger = get_logger("app.log")


def format_value(x, precision, unit):
    """Format a value with precision and unit, handling both numeric and string types."""
    if pd.isna(x):
        return ""  # Return empty string instead of "N/A"
    # Try to convert to float for numeric formatting
    try:
        numeric_val = float(x)
        return f"{numeric_val:.{precision}f}{unit}"
    except (ValueError, TypeError):
        # If conversion fails, treat as string
        return str(x)


def _build_multi_indicator_table(plot_df, indicators_list, indicators_meta_dict, dataset_id):
    """Build a table dataframe and subtitle metadata without the key column."""
    logger.info(f"Building multi-indicator table with indicators: {indicators_list}")
    logger.info(f"Input dataframe has {len(plot_df)} rows")
    logger.info(f"Available columns in input df: {list(plot_df.columns)}")
    
    # Create a clean dataframe with formatted indicator columns only.
    display_df = plot_df.copy()
    
    if 'geometry' in display_df.columns:
        display_df = display_df.drop(columns=['geometry'])
    
    result_df = pd.DataFrame(index=display_df.index).reset_index(drop=True)
    column_subtitles = {}
    logger.info(f"Result df initialized without key column: {len(result_df)} rows")
    
    # Add each indicator as a formatted column
    for ind_name in indicators_list:
        if ind_name not in display_df.columns:
            logger.warning(f"Indicator column '{ind_name}' not found in dataframe")
            continue
        
        # Get the metadata for this indicator
        variant_meta = next(
            (v for v in indicators_meta_dict[ind_name] if v.get("dataset") == dataset_id),
            indicators_meta_dict[ind_name][0] if indicators_meta_dict[ind_name] else {}
        )
        
        precision = variant_meta.get("precision", 1)
        unit = variant_meta.get("unit", "")
        title = variant_meta.get("title", ind_name)
        subtitle = variant_meta.get("subtitle", "")
        
        # Format the indicator column - handle both numeric and string values
        formatted_col = display_df[ind_name].apply(lambda x: format_value(x, precision, unit))
        # Reset index to match result_df's index to avoid NaN alignment issues
        formatted_col = formatted_col.reset_index(drop=True)
        result_df[title] = formatted_col
        column_subtitles[title] = subtitle
        non_empty_count = (formatted_col != "").sum()
        logger.info(f"Added indicator '{ind_name}' as '{title}' - non-empty values: {non_empty_count}/{len(formatted_col)}")
    
    logger.info(f"Result df before row filtering: {len(result_df)} rows, columns: {list(result_df.columns)}")
    
    # Filter out rows where all indicator columns are empty
    indicator_columns = list(result_df.columns)
    logger.info(f"Checking {len(indicator_columns)} indicator columns for data: {indicator_columns}")
    
    # Debug: show first few rows before filtering
    logger.info(f"First row values: {result_df[indicator_columns].iloc[0].to_dict() if len(result_df) > 0 else 'empty'}")
    
    def row_has_data(row):
        """Check if a row has any non-empty indicator values."""
        has_any = False
        for val in row:
            str_val = str(val).strip() if pd.notna(val) else ""
            if str_val != "":
                has_any = True
                break
        return has_any
    
    # Apply the filtering
    mask = result_df[indicator_columns].apply(row_has_data, axis=1)
    logger.info(f"Rows with data (True in mask): {mask.sum()}")
    logger.info(f"First 10 mask values: {mask.head(10).tolist()}")
    
    result_df = result_df[mask].reset_index(drop=True)
    logger.info(f"Result df after row filtering: {len(result_df)} rows")

    return result_df, column_subtitles


def get_table_fig(
    plot_gdf,
    dataset_meta,
    dataset_id,
    indicators_meta_dict,
    selected_option=None
):
    """
    Build a table visualization showing multiple indicators.
    
    This function handles:
    - Applying option filters to the data
    - Collecting all table-type indicators for the dataset
    - Deduplicating rows based on table display columns
    - Building the multi-indicator table
    
    Args:
        plot_gdf: GeoDataFrame with geographic and indicator data
        dataset_meta: Metadata dict for this dataset (contains key, options, etc.)
        dataset_id: String identifier for the dataset
        indicators_meta_dict: Dict of all indicator metadata
        selected_option: Dict or string of selected filter options
    
    Returns:
        Tuple of dataframe and per-column subtitle metadata
    """
    
    # Apply selected_option filters to plot_gdf before building the table
    filtered_plot_gdf = plot_gdf.copy()
    logger.info(f"Table view - rows before option filters: {len(filtered_plot_gdf)}")
    
    if selected_option is not None:
        logger.info(f"Applying option filters: {selected_option}")
        if isinstance(selected_option, dict):
            for col, value in selected_option.items():
                if col in filtered_plot_gdf.columns:
                    filtered_plot_gdf = filtered_plot_gdf[filtered_plot_gdf[col] == value]
                    logger.info(f"After filtering '{col}' = '{value}': {len(filtered_plot_gdf)} rows")
        elif isinstance(selected_option, str):
            # Single column case
            option_columns = dataset_meta.get("options", [])
            if option_columns and option_columns[0] in filtered_plot_gdf.columns:
                filtered_plot_gdf = filtered_plot_gdf[filtered_plot_gdf[option_columns[0]] == selected_option]
                logger.info(f"After filtering single option: {len(filtered_plot_gdf)} rows")
    
    logger.info(f"Table view - rows after option filters: {len(filtered_plot_gdf)}")
    
    # Get all table-type indicators for this dataset
    all_indicators = []
    for ind_name, variants in indicators_meta_dict.items():
        for v in variants:
            if v.get("dataset") == dataset_id and v.get("visualization_type") == "table":
                all_indicators.append(ind_name)
                break
    
    # Filter to only those that exist in the dataframe
    all_indicators = [ind for ind in all_indicators if ind in filtered_plot_gdf.columns]
    
    # Deduplicate based only on columns that appear in the table
    # (key column + option columns + indicator columns)
    if len(filtered_plot_gdf) > 0:
        data_key = dataset_meta["key"]
        option_columns = dataset_meta.get("options", [])
        
        # Build list of columns that will be in the table
        table_columns = [data_key] + option_columns + all_indicators
        table_columns = [col for col in table_columns if col in filtered_plot_gdf.columns]
        
        if table_columns:
            duplicates_count = filtered_plot_gdf.duplicated(subset=table_columns, keep=False).sum()
            if duplicates_count > 0:
                logger.info(f"Found {duplicates_count} duplicate rows (based on table display columns)")
                filtered_plot_gdf = filtered_plot_gdf.drop_duplicates(subset=table_columns, keep="first")
                logger.info(f"After deduplication: {len(filtered_plot_gdf)} rows")
    
    if all_indicators:
        table_df, column_subtitles = _build_multi_indicator_table(
            filtered_plot_gdf,
            all_indicators,
            indicators_meta_dict,
            dataset_id
        )
        return table_df, column_subtitles
    else:
        return None
