import pandas as pd
import json
import os
import numpy as np
from datetime import datetime

# =========================
# 📂 FILE PATHS
# =========================
json_path = "mesh_alpha_users.json"

csv_files = [
    "datalake/corteca_station_daily_108.csv",
    "datalake/corteca_daily_108.csv",

    # "datalake/corteca_station_daily_102.csv",
    # "datalake/corteca_daily_102.csv",

    "datalake/corteca_station_daily_105.csv",
    "datalake/corteca_daily_105.csv",
]

# =========================
# LOAD JSON
# =========================
with open(json_path, "r") as f:
    users = json.load(f)

users_df = pd.DataFrame(users)

users_df["serial"] = users_df["serial"].astype(str).str.strip().str.upper()
users_df["mac"] = (
    users_df["mac"]
    .astype(str)
    .str.replace("-", "", regex=False)
    .str.replace(":", "", regex=False)
    .str.upper()
)

# =========================
# AUTO DETECT COLS
# =========================
def find_col(df, keywords):
    for col in df.columns:
        for k in keywords:
            if k in col:
                return col
    return None

# =========================
# NORMALIZE
# =========================
def normalize(df, serial_col, mac_col):
    if serial_col:
        df[serial_col] = (
            df[serial_col]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if mac_col:
        df[mac_col] = (
            df[mac_col]
            .astype(str)
            .str.replace("-", "", regex=False)
            .str.replace(":", "", regex=False)
            .str.upper()
        )

    return df

# =========================
# FILTER
# =========================
serial_list = users_df["serial"].dropna().unique()
mac_list = users_df["mac"].dropna().unique()

def filter_df(df, serial_col, mac_col):
    cond = pd.Series(False, index=df.index)

    if serial_col:
        cond |= df[serial_col].isin(serial_list)

    if mac_col:
        cond |= df[mac_col].isin(mac_list)

    return df[cond]

# =========================
# PROCESS ALL FILES
# =========================
filtered_dfs = []

for file in csv_files:

    print(f"📂 Processing: {file}")

    try:
        df = pd.read_csv(file)

        # normalize columns
        df.columns = df.columns.str.lower().str.strip()

        # detect cols
        serial_col = find_col(df, ["serial"])
        mac_col = find_col(df, ["mac"])

        # normalize values
        df = normalize(df, serial_col, mac_col)

        # filter
        filtered_df = filter_df(df, serial_col, mac_col)

        print(f"✅ Matched Rows: {len(filtered_df)}")

        filtered_dfs.append(filtered_df)

    except Exception as e:
        print(f"❌ Error processing {file}: {e}")

# =========================
# MERGE ALL
# =========================
final_df = pd.concat(filtered_dfs, ignore_index=True)

# =========================
# REMOVE DUPLICATES
# =========================
final_df = final_df.drop_duplicates()

# =====================================================================
# 🔧 COLUMN NORMALIZATION  (NEW — fixes dashboard compatibility)
# =====================================================================
# After concat, corteca_station rows have "client_with_*" columns while
# corteca_daily (pod) rows have friendly-name columns like
# "poor coverage (overall)".
# The dashboard expects everything under "ap_with_*" / underscore names.
# This block copies data into the canonical column names so every row
# has the fields the dashboard reads.
# =====================================================================

def fill_column(df, src, dst):
    """Copy src → dst wherever dst is missing but src has a value."""
    if src not in df.columns:
        return
    if dst not in df.columns:
        df[dst] = np.nan
    mask = df[dst].isna() & df[src].notna()
    df.loc[mask, dst] = df.loc[mask, src]

# --- 1. Identifier / structural columns ---
ident_map = {
    "ont serial number":  "ont_serial_no",
    "ap name":            "ap",
    "mac address":        "mac_address",
    "connected clients":  "station_count",
    "circle code":        "circle_code_no",
    "vendor":             "vendor_name",
    "ap manufacturer":    "ap_manufacturer",
}
for src, dst in ident_map.items():
    fill_column(final_df, src, dst)

# --- 2. client_with_* → ap_with_* (metric + breach + sample-count) ---
client_to_ap = {
    "client_with_poor_coverage":                                    "ap_with_poor_coverage",
    "client_with_poor_coverage_2":                                  "ap_with_poor_coverage_2",
    "client_with_poor_coverage_5":                                  "ap_with_poor_coverage_5",
    "client_with_poor_snr_sample":                                  "ap_with_poor_snr_sample",
    "client_with_poor_snr_sample_2":                                "ap_with_poor_snr_sample_2",
    "client_with_poor_snr_sample_5":                                "ap_with_poor_snr_sample_5",
    "client_with_poor_link_speed_mcs_rate":                         "ap_with_poor_link_speed_mcs_rate",
    "client_with_poor_link_speed_mcs_rate_2":                       "ap_with_poor_link_speed_mcs_rate_2",
    "client_with_poor_link_speed_mcs_rate_5":                       "ap_with_poor_link_speed_mcs_rate_5",
    "client_with_high_client_disconnection":                        "ap_with_high_client_disconnection",
    "client_with_high_tx_packet_error":                             "ap_with_high_tx_packet_error",
    "client_with_poor_dl_throughput_less_than_threshold":            "ap_with_poor_dl_throughput_less_than_threshold",
    "client_with_poor_ul_throughput_less_than_threshold":            "ap_with_poor_ul_throughput_less_than_threshold",
    "client_with_high_no_of_sticky_client_2_with_good_coverage":    "ap_with_high_no_of_sticky_client_2_with_good_coverage",
    "client_with_high_no_of_sticky_client_5_with_poor_coverage":    "ap_with_high_no_of_sticky_client_5_with_poor_coverage",
    # breach flags
    "client_with_poor_coverage_breach":                             "ap_with_poor_coverage_breach",
    "client_with_poor_coverage_2_breach":                           "ap_with_poor_coverage_2_breach",
    "client_with_poor_coverage_5_breach":                           "ap_with_poor_coverage_5_breach",
    "client_with_poor_snr_sample_breach":                           "ap_with_poor_snr_sample_breach",
    "client_with_poor_snr_sample_2_breach":                         "ap_with_poor_snr_sample_2_breach",
    "client_with_poor_snr_sample_5_breach":                         "ap_with_poor_snr_sample_5_breach",
    "client_with_poor_link_speed_mcs_rate_breach":                  "ap_with_poor_link_speed_mcs_rate_breach",
    "client_with_poor_link_speed_mcs_rate_2_breach":                "ap_with_poor_link_speed_mcs_rate_2_breach",
    "client_with_poor_link_speed_mcs_rate_5_breach":                "ap_with_poor_link_speed_mcs_rate_5_breach",
    "client_with_high_client_disconnection_breach":                 "ap_with_high_client_disconnection_breach",
    "client_with_high_tx_packet_error_breach":                      "ap_with_high_tx_packet_error_breach",
    # sample counts
    "count_of_total_samples_for_client_with_poor_snr_sample":       "count_of_total_samples_for_ap_with_poor_snr_sample",
    "count_of_total_samples_for_client_with_poor_snr_sample_2":     "count_of_total_samples_for_ap_with_poor_snr_sample_2",
    "count_of_total_samples_for_client_with_poor_snr_sample_5":     "count_of_total_samples_for_ap_with_poor_snr_sample_5",
    "count_of_total_samples_for_client_with_high_tx_packet_error":  "count_of_total_samples_for_ap_with_high_tx_packet_error",
    "count_of_total_samples_for_client_with_poor_link_speed_mcs_rate":   "count_of_total_samples_for_ap_with_poor_link_speed_mcs_rate",
    "count_of_total_samples_for_client_with_poor_link_speed_mcs_rate_2": "count_of_total_samples_for_ap_with_poor_link_speed_mcs_rate_2",
    "count_of_total_samples_for_client_with_poor_link_speed_mcs_rate_5": "count_of_total_samples_for_ap_with_poor_link_speed_mcs_rate_5",
    "count_of_total_samples_for_client_with_poor_coverage":         "count_of_total_samples_for_ap_with_poor_coverage",
    "count_of_total_samples_for_client_with_poor_coverage_2":       "count_of_total_samples_for_ap_with_poor_coverage_2",
    "count_of_total_samples_for_client_with_poor_coverage_5":       "count_of_total_samples_for_ap_with_poor_coverage_5",
}
for src, dst in client_to_ap.items():
    fill_column(final_df, src, dst)

# --- 3. Friendly (human-readable) → ap_with_* (for pod / daily rows) ---
friendly_to_ap = {
    "poor coverage (overall)":            "ap_with_poor_coverage",
    "poor coverage (2.4 ghz)":            "ap_with_poor_coverage_2",
    "poor coverage (5 ghz)":              "ap_with_poor_coverage_5",
    "poor snr (overall)":                 "ap_with_poor_snr_sample",
    "poor snr (2.4 ghz)":                 "ap_with_poor_snr_sample_2",
    "poor snr (5 ghz)":                   "ap_with_poor_snr_sample_5",
    "low download throughput (overall)":   "ap_with_poor_dl_throughput_less_than_threshold",
    "low upload throughput (overall)":     "ap_with_poor_ul_throughput_less_than_threshold",
    "low link speed (overall)":            "ap_with_poor_link_speed_mcs_rate",
    "low link speed (2.4 ghz)":            "ap_with_poor_link_speed_mcs_rate_2",
    "low link speed (5 ghz)":              "ap_with_poor_link_speed_mcs_rate_5",
    "high interference (overall)":         "ap_with_high_interference",
    "high interference (2.4 ghz)":         "ap_with_high_interference_2",
    "high interference (5 ghz)":           "ap_with_high_interference_5",
    "high client disconnections (overall)":"ap_with_high_client_disconnection",
    "high retry rate (overall)":           "ap_with_high_retry_rate",
    "high tx packet errors (overall)":     "ap_with_high_tx_packet_error",
    "tx packet error (%) (overall)":       "ap_with_high_tx_packet_error_percent",
    "high tx packet errors flag (overall)":"ap_with_high_tx_packet_error_flag",
    "high rx packet errors (overall)":     "ap_with_high_rx_packet_error",
    "high rx packet errors flag (overall)":"ap_with_high_rx_packet_error_flag",
    "downtime (%) (overall)":              "ap_downtime_per",
    "high cpu utilization (overall)":      "ap_with_high_cpu_utilisation",
    "memory errors (overall)":             "ap_with_high_memory_packet_error",
    "sticky clients (2.4 ghz, good coverage)":  "ap_with_high_no_of_sticky_client_2_with_good_coverage",
    "sticky clients (5 ghz, poor coverage)":    "ap_with_high_no_of_sticky_client_5_with_poor_coverage",
    "poor tot on (5 ghz)":                 "ap_with_poor_tot_on_5g",
    "zero usage aps (overall)":            "ap_with_zero_usage",
    "channel utilization (%) (overall)":   "ap_with_high_channel_utilisation_pct",
    "high channel utilization count (overall)":    "ap_with_high_channel_utilisation_count",
    "total channels (all bands)":          "total_channels_all",
    "high channel utilization (2.4 ghz) (%)":      "ap_with_high_channel_utilisation_2_pct",
    "high channel utilization count (2.4 ghz)":    "ap_with_high_channel_utilisation_2_count",
    "total channels (2.4 ghz)":            "total_channels_2",
    "high channel congestion (5 ghz) (%)": "ap_with_high_channel_congestion_5_pct",
    "high channel congestion count (5 ghz)":       "ap_with_high_channel_congestion_5_count",
    "total channels (5 ghz)":              "total_channels_5",
    "obss (overall)":                      "channelobss",
    "obss2 4 (overall)":                   "channelobss2_4",
    "obss5 (overall)":                     "channelobss5",
    # breach flags
    "poor coverage breach (overall)":      "ap_with_poor_coverage_breach",
    "poor coverage breach (2.4 ghz)":      "ap_with_poor_coverage_2_breach",
    "poor coverage breach (5 ghz)":        "ap_with_poor_coverage_5_breach",
    "poor snr breach (overall)":           "ap_with_poor_snr_sample_breach",
    "poor snr breach (2.4 ghz)":           "ap_with_poor_snr_sample_2_breach",
    "poor snr breach (5 ghz)":             "ap_with_poor_snr_sample_5_breach",
    "low download throughput breach (overall)":    "ap_with_poor_dl_throughput_less_than_threshold_breach",
    "low upload throughput breach (overall)":      "ap_with_poor_ul_throughput_less_than_threshold_breach",
    "low link speed breach (overall)":     "ap_with_poor_link_speed_mcs_rate_breach",
    "low link speed breach (2.4 ghz)":     "ap_with_poor_link_speed_mcs_rate_2_breach",
    "low link speed breach (5 ghz)":       "ap_with_poor_link_speed_mcs_rate_5_breach",
    "high interference breach (overall)":  "ap_with_high_interference_breach",
    "high interference breach (2.4 ghz)":  "ap_with_high_interference_2_breach",
    "high interference breach (5 ghz)":    "ap_with_high_interference_5_breach",
    "high client disconnections breach (overall)": "ap_with_high_client_disconnection_breach",
    "high retry rate breach (overall)":    "ap_with_high_retry_rate_breach",
    "high tx packet errors breach (overall)":      "ap_with_high_tx_packet_error_breach",
    "tx packet error (%) breach (overall)":"ap_with_high_tx_packet_error_percent_breach",
    "high rx packet errors breach (overall)":      "ap_with_high_rx_packet_error_breach",
    "ap downtime (%) breach (overall)":    "ap_downtime_per_breach",
    "internet down incidents breach (overall)":    "ap_with_high_internet_down_incident_breach",
    "high cpu utilization breach (overall)":"ap_with_high_cpu_utilisation_breach",
    "memory errors breach (overall)":      "ap_with_high_memory_packet_error_breach",
    "sticky clients breach (2.4 ghz, good coverage)":  "ap_with_high_no_of_sticky_client_2_with_good_coverage_breach",
    "sticky clients breach (5 ghz, poor coverage)":    "ap_with_high_no_of_sticky_client_5_with_poor_coverage_breach",
    "poor tot on breach (5 ghz)":          "ap_with_poor_tot_on_5g_breach",
    "zero usage aps breach (overall)":     "ap_with_zero_usage_breach",
    "high channel utilisation breach (overall)":   "ap_with_high_channel_utilisation_breach",
    "high channel utilisation breach (2.4 ghz)":   "ap_with_high_channel_utilisation_2_breach",
    "high channel congestion breach (5 ghz)":      "ap_with_high_channel_congestion_5_breach",
    "obss breach (overall)":               "channelobss_breach",
    "obss2 4 breach (overall)":            "channelobss2_4_breach",
    "obss5 breach (overall)":              "channelobss5_breach",
}
for src, dst in friendly_to_ap.items():
    fill_column(final_df, src, dst)

print(f"🔧 Column normalization complete.")
# =====================================================================

# =========================
# 📁 CREATE OUTPUT FOLDER
# =========================
output_dir = "filtered_data"
os.makedirs(output_dir, exist_ok=True)

# =========================
# 🕒 OUTPUT FILE
# =========================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

output_file = os.path.join(
    output_dir,
    f"filtered_mesh_output_15_June_2026.csv"
)

# =========================
# SAVE
# =========================

final_df.columns = final_df.columns.str.replace(",", " -", regex=False)

final_df.to_csv(output_file, index=False)

print("\n==========================")
print(f"✅ File saved: {output_file}")
print(f"📊 Total Rows: {len(final_df)}")
print("==========================")




# import pandas as pd
# import json
# import os
# from datetime import datetime

# # =========================
# # 📂 FILE PATHS
# # =========================
# json_path = "mesh_alpha_users.json"

# file1 = "datalake/corteca_station_daily_108.csv"
# file2 = "datalake/corteca_daily_108.csv"

# # =========================
# # LOAD JSON
# # =========================
# with open(json_path, "r") as f:
#     users = json.load(f)

# users_df = pd.DataFrame(users)

# users_df["serial"] = users_df["serial"].str.strip().str.upper()
# users_df["mac"] = users_df["mac"].str.replace("-", "", regex=False).str.upper()

# # =========================
# # LOAD CSVs
# # =========================
# df1 = pd.read_csv(file1)
# df2 = pd.read_csv(file2)

# df1.columns = df1.columns.str.lower().str.strip()
# df2.columns = df2.columns.str.lower().str.strip()

# # =========================
# # AUTO DETECT COLS
# # =========================
# def find_col(df, keywords):
#     for col in df.columns:
#         for k in keywords:
#             if k in col:
#                 return col
#     return None

# serial_col_1 = find_col(df1, ["serial"])
# mac_col_1 = find_col(df1, ["mac"])

# serial_col_2 = find_col(df2, ["serial"])
# mac_col_2 = find_col(df2, ["mac"])

# # =========================
# # NORMALIZE
# # =========================
# def normalize(df, serial_col, mac_col):
#     if serial_col:
#         df[serial_col] = df[serial_col].astype(str).str.strip().str.upper()
#     if mac_col:
#         df[mac_col] = df[mac_col].astype(str).str.replace("-", "", regex=False).str.upper()
#     return df

# df1 = normalize(df1, serial_col_1, mac_col_1)
# df2 = normalize(df2, serial_col_2, mac_col_2)

# # =========================
# # FILTER
# # =========================
# serial_list = users_df["serial"].dropna().unique()
# mac_list = users_df["mac"].dropna().unique()

# def filter_df(df, serial_col, mac_col):
#     cond = pd.Series([False]*len(df))

#     if serial_col:
#         cond = cond | df[serial_col].isin(serial_list)

#     if mac_col:
#         cond = cond | df[mac_col].isin(mac_list)

#     return df[cond]

# filtered_df1 = filter_df(df1, serial_col_1, mac_col_1)
# filtered_df2 = filter_df(df2, serial_col_2, mac_col_2)

# # =========================
# # MERGE
# # =========================
# final_df = pd.concat([filtered_df1, filtered_df2], ignore_index=True)

# # =========================
# # 📁 CREATE OUTPUT FOLDER
# # =========================
# output_dir = "filtered_data"
# os.makedirs(output_dir, exist_ok=True)

# # =========================
# # 🕒 TIMESTAMPED FILE NAME
# # =========================
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# output_file = os.path.join(
#     output_dir,
#     f"filtered_mesh_output_6_May_2026.csv"
# )

# # =========================
# # SAVE
# # =========================
# final_df.to_csv(output_file, index=False)

# print(f"✅ File saved: {output_file}")
# print(f"📊 Rows: {len(final_df)}")


# import pandas as pd
# import json
# import os
# from datetime import datetime

# # =========================
# # 📂 FILE PATHS
# # =========================
# json_path = "mesh_alpha_users.json"

# file1 = "datalake/corteca_station_daily_108.csv"
# file2 = "datalake/corteca_daily_108.csv"
# file3 = "datalake/required_mesh_data_13april_tp_19april.csv"  # ✅ NEW

# # =========================
# # LOAD JSON
# # =========================
# with open(json_path, "r") as f:
#     users = json.load(f)

# users_df = pd.DataFrame(users)

# users_df["serial"] = users_df["serial"].str.strip().str.upper()
# users_df["mac"] = users_df["mac"].str.replace("-", "", regex=False).str.upper()

# # =========================
# # LOAD CSVs
# # =========================
# df1 = pd.read_csv(file1)
# df2 = pd.read_csv(file2)
# df3 = pd.read_csv(file3)  # ✅ NEW

# # Normalize column names
# for df in [df1, df2, df3]:
#     df.columns = df.columns.str.lower().str.strip()

# # =========================
# # AUTO DETECT COLS
# # =========================
# def find_col(df, keywords):
#     for col in df.columns:
#         for k in keywords:
#             if k in col:
#                 return col
#     return None

# serial_col_1 = find_col(df1, ["serial"])
# mac_col_1 = find_col(df1, ["mac"])

# serial_col_2 = find_col(df2, ["serial"])
# mac_col_2 = find_col(df2, ["mac"])

# serial_col_3 = find_col(df3, ["serial"])   # ✅ NEW
# mac_col_3 = find_col(df3, ["mac"])         # ✅ NEW

# # =========================
# # NORMALIZE
# # =========================
# def normalize(df, serial_col, mac_col):
#     if serial_col:
#         df[serial_col] = df[serial_col].astype(str).str.strip().str.upper()
#     if mac_col:
#         df[mac_col] = df[mac_col].astype(str).str.replace("-", "", regex=False).str.upper()
#     return df

# df1 = normalize(df1, serial_col_1, mac_col_1)
# df2 = normalize(df2, serial_col_2, mac_col_2)
# df3 = normalize(df3, serial_col_3, mac_col_3)  # ✅ NEW

# # =========================
# # FILTER
# # =========================
# serial_list = users_df["serial"].dropna().unique()
# mac_list = users_df["mac"].dropna().unique()

# def filter_df(df, serial_col, mac_col):
#     cond = pd.Series([False]*len(df))

#     if serial_col:
#         cond = cond | df[serial_col].isin(serial_list)

#     if mac_col:
#         cond = cond | df[mac_col].isin(mac_list)

#     return df[cond]

# filtered_df1 = filter_df(df1, serial_col_1, mac_col_1)
# filtered_df2 = filter_df(df2, serial_col_2, mac_col_2)
# filtered_df3 = filter_df(df3, serial_col_3, mac_col_3)  # ✅ NEW

# # =========================
# # MERGE (ALL 3)
# # =========================
# final_df = pd.concat(
#     [filtered_df1, filtered_df2, filtered_df3],
#     ignore_index=True
# )

# # =========================
# # 📁 CREATE OUTPUT FOLDER
# # =========================
# output_dir = "filtered_data"
# os.makedirs(output_dir, exist_ok=True)

# # =========================
# # 🕒 TIMESTAMPED FILE NAME
# # =========================
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# output_file = os.path.join(
#     output_dir,
#     f"filtered_mesh_output_22_April_2026.csv"
# )

# # =========================
# # SAVE
# # =========================
# final_df.to_csv(output_file, index=False)

# print(f"✅ File saved: {output_file}")
# print(f"📊 Rows: {len(final_df)}")
# print(f"📦 Sources merged: 3 (station + daily + required_mesh)")