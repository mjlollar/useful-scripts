## Script that identifies rows containing PMBB IDs in two files and merges them, retaining all rows and keeping --filea (-a) ID columns (Union of A and B, retain A intersections and column name)
## Example use would be merging a phenotype file to a list of IDs, or genotype to phenotype data
## Script infers which columns are the ID columns, but has optional flags to hard-pass those into the script.

import argparse
import pandas as pd
import re

parser = argparse.ArgumentParser(description="Combine two files on inferred ID column and output result to new tsv. Left joins -fileA to -fileB")
parser.add_argument('-a', '--filea', type=str, required=True, help="Path to file that will be left of left join.")
parser.add_argument('-aid', type=str, required=False, help="ID column name of File A")
parser.add_argument('-b', '--fileb', type=str, required=True, help="Path to second File.")
parser.add_argument('-bid', type=str, required=False, help="ID column name of FileB", )
parser.add_argument('-o', '--output', type=str, required=True, help="Output file name/path.")
args = parser.parse_args()

if args.aid and not args.bid:
	parser.error("-bid is required if -aid is supplied.")
if args.bid and not args.aid:
	parser.error("-aid is required if -bid is supplied.")


ID_PATTERN = r"PMBB\d+"
ID_COL_A = None
ID_COL_B = None

if args.aid:
	ID_COL_A = args.aid
	ID_COL_B = args.bid


## Method to detect columns with PMBB IDs
## Detects based on first row of every column, fails if multiple matches to pattern
def detect_id_column(df, label):
	if df.empty:
		raise ValueError(f"{label} has no rows to detect an ID column from.")

	first_row = df.iloc[0]
	matches = [
		col for col in df.columns
		if pd.notna(first_row[col]) and re.fullmatch(ID_PATTERN, first_row[col].strip())]
	if not matches:
		raise ValueError(f"No value in the first row of {label} matches '{ID_PATTERN}'.")
	if len(matches) > 1:
		raise ValueError(f"Multiple matching column IDs found in {label}.")

	return matches[0]


## Main Method, join file B to file A on PMBB ID
## Drops file B's PMBB ID column, keeps all other columns in both files.
def main():
	df_a = pd.read_csv(args.filea, sep='\t', dtype=str)
	df_b = pd.read_csv(args.fileb, sep='\t', dtype=str)

	id_a = ID_COL_A or detect_id_column(df_a, "File A")
	id_b = ID_COL_B or detect_id_column(df_b, "File B")

	df_a[id_a] = df_a[id_a].str.strip()
	df_b[id_b] = df_b[id_b].str.strip()

	# Give File B's ID column temp name so no collision chance
	temp_id = "__id_from_b__"
	df_b = df_b.rename(columns={id_b: temp_id})

	# Repeated IDs in File B would duplicate File A rows; keep the first one
	dupes = df_b[temp_id].duplicated().sum()
	if dupes:
		print(f"Warning: {dupes} duplicate IDs in File B; keeping first occurrence of each.")
		df_b = df_b.drop_duplicates(subset=temp_id, keep="first")

	merged = df_a.merge(
		df_b,
		how="left",
		left_on=id_a,
		right_on=temp_id,
		suffixes=("", "_dupcol"),   # tags any File B column whose name clashes with File A
	)
	merged = merged.drop(columns=temp_id)

	merged.to_csv(args.output, index=False, sep='\t')
	print(f"Saved to {args.output}")


if __name__ == "__main__":
	main()
