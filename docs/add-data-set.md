# Adding a Data Set

Each data set requires a CSV file and a corresponding metadata file.

1. Place the CSV file in `data/indicatoren`. For example, use
   `data/indicatoren/my_dataset.csv`.
2. Create a metadata file in `metadata`, such as `metadata/my_dataset.meta.yaml`.
   Do not use `example.meta.yaml` directly: the application deliberately skips
   that file when loading metadata.
3. Set `dataset_id` in the metadata file to the CSV filename without the
   `.csv` extension. For the example above, use `dataset_id: my_dataset`.
4. Set `key` to the name of the CSV column that identifies the area or record.
5. Add an entry under `indicators` for every CSV column that should be available
   in the dashboard. Each entry must use the CSV column name as its key and
   define its display properties, including `title`, `subtitle`, `description`,
   `legend`, `theme`, `subject`, `visualization_type`, and `link`.

Use [metadata/example.meta.yaml](../metadata/example.meta.yaml) as a template
for the metadata structure. When the data set should be displayed on a map,
also configure the geographic boundary fields: `gwb_version`, `layer_naam`,
`key_gwb`, and `area_name_field`. The value in `key` must match the identifier
in the CSV, and `key_gwb` must match the corresponding identifier in the
configured geographic boundary layer.

Restart the dashboard after adding or changing data files or metadata so that
the application reloads them.