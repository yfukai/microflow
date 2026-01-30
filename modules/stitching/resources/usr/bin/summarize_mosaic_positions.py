#!/usr/bin/env python3
import pyrallis
import os
import pandas as pd
from dataclasses import dataclass

@dataclass
class Config:
    file_path : str = "testdata/mosaic_positions.csv"
    output_path : str = "testdata/test_output"
    output_filename : str = "summarized_mosaic_positions.csv"
    
def main():
    cfg = pyrallis.parse(Config)
    df = pd.read_csv(cfg.file_path)
    df["y_pos"] = df["y_pos"] - df["y_pos"].mean()
    df["x_pos"] = df["x_pos"] - df["x_pos"].mean()
    median_positions = df.groupby(["row","col"])[["y_pos", "x_pos"]].median().reset_index()
    abs_diffs = []
    for T, grp in df.groupby("T"):
        m =median_positions.set_index(["row", "col"])[["x_pos", "y_pos"]]
        target = grp.set_index(["row", "col"])[["x_pos", "y_pos"]]
        abs_diff = (target - m).abs().mean().to_dict()
        abs_diff["T"] = T
        abs_diffs.append(abs_diff)
    abs_diffs_df = pd.DataFrame(abs_diffs)
    T=abs_diffs_df.loc[(abs_diffs_df["y_pos"] + abs_diffs_df["x_pos"]).idxmin()]["T"]
    output_path = os.path.join(cfg.output_path, cfg.output_filename)
    df[df["T"]==T].to_csv(output_path, index=False)

if __name__ == "__main__":
    main()