# Mesh Alpha Trial User Report Generation

This script parses Mesh Alpha trial users from `mesh_alpha_users.json` and generates a CSV report for the Mesh installation dashboard.

## Setup

1. Create a `datalake` directory.
2. Copy the following report files into the directory:

   * `corteca_daily_105.csv`
   * `corteca_daily_108.csv`
   * `corteca_station_daily_105.csv`
   * `corteca_station_daily_108.csv`

> **Note:** Circle **105** represents HR and **108** represents KK. Since all Mesh Alpha trial users belong to these two circles, only these reports are required.

## Configuration

Before running the script, update the report filename on **line 305** of `filter_datalake.py` to match the current report date.

## Run

```bash
python3 filter_datalake.py
```

The script typically takes **20–30 seconds** to complete.

## Output

A parsed CSV file will be generated in the `filtered_data` directory.

## Dashboard Update

1. Upload the generated CSV file from `filtered_data` to the dashboard repository.
2. Update the report filename reference in `index.html`.
3. Deploy or refresh the dashboard to view the latest data.
