import pandas as pd
import argparse
from datetime import datetime
from collections import defaultdict 
"""
Transaction CSV file format:
CSV column separator: ","
CSV columns expected:
<Entity>: Name of MF/Equity
<Units>: Units purchased. Should be negative if units are sold
<Price>: Price at which the units were purchased/sold. Must be positive
<Date>: Transaction Date, format: dd-mon-yyyy e.g. 01-Jan-1990

Metadata file format:
CSV column separator: ","
CSV columns expected:
<Entity>: Name of MF/Equity
<LongTermDays>: Number of days after which the long term capital gains is applicable
<FundType>: One of debt, equity, commodity

CII Table file format:
CSV column separator: ","
<FYYear>: Financial year e.g. 2018-19
<CII>: CII number e.g. 280
"""

def compute_txn_df(args):
    df = pd.read_csv(args["txn_file"])
    metadata_df = pd.read_csv(args["metadata_file"])
    long_term_days_dict = {}
    for _, row in metadata_df.iterrows():
        long_term_days_dict[row.Entity] = row.LongTermDays
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y")
    df = df.sort_values("Date").reset_index(drop=True)

    start_year = int(args["fy_year"].split("-")[0])
    start_date = datetime.strptime("{0}-04-01".format(start_year), "%Y-%m-%d")
    end_date = datetime.strptime("{0}-03-31".format(start_year+1), "%Y-%m-%d")
    # Compute the tax implications for each entity
    txn_df = pd.DataFrame(columns=["Entity", "txn_type", "CostOfAcquisition", "FairValue", "Date"])
    for sale_index, sale_row in df.iterrows():
        # The dataframe is sorted by date
        if sale_row.Date > end_date:
            break
        
        if sale_row.Units < 0: # sale transaction
            # Go back and find out the matching transaction
            for buy_index, buy_row in df.iterrows():
                sale_row = df.iloc[sale_index]
                if sale_row.Entity != buy_row.Entity:
                    continue
                if sale_row.Units >= 0:
                    break
                if buy_row.Date > sale_row.Date:
                    break

                if buy_row.Units > 0:
                    # buy transaction, map the transaction
                    if buy_row.Units + sale_row.Units >= 0:
                        units_consumed = -sale_row.Units
                        df.loc[buy_index, "Units"] = buy_row.Units + sale_row.Units
                        df.loc[sale_index, "Units"] = 0
                    else:
                        units_consumed = buy_row.Units
                        df.loc[sale_index, "Units"] = sale_row.Units + buy_row.Units
                        df.loc[buy_index, "Units"] = 0

                    if sale_row.Date < start_date:
                        continue

                    days_delta = (sale_row.Date - buy_row.Date).days
                    is_long_term = days_delta > long_term_days_dict[sale_row.Entity]
                    txn_df = txn_df.append({'Entity': sale_row.Entity, 'txn_type': 'long_term' if is_long_term else 'short_term',
                            'Units': units_consumed,
                            "SalePrice": sale_row.Price, "FairPrice" : buy_row.Price,
                            'CostOfAcquisition': (buy_row.Price * units_consumed), 'FairValue': (sale_row.Price * units_consumed),
                            'Date': sale_row.Date, 'BuyDate': buy_row.Date}, ignore_index=True)


            if df.loc[sale_index, "Units"] < -0.001:
                raise ValueError("Couldn't offset sale transaction for entry: {0}\n, df: \n{1}\n".format(sale_row, df))

    txn_df = txn_df.sort_values(["Entity", 'Date']).reset_index(drop=True)
    return txn_df


def compute_profit_summary(txn_df, profit_intervals):
    profit_dict = defaultdict(int)
    for _, txn in txn_df.iterrows():
        for interval in profit_intervals:
            if is_txn_in_interval(txn, interval):
                profit_dict[interval] += txn.FairValue - txn.CostOfAcquisition
    return profit_dict

def is_txn_in_interval(txn, interval):
    return txn.Date >= interval[0] and txn.Date <= interval[1]

def preprocess_args(args):
    new_args = args.copy()
    if 'profit_intervals' not in args:
        return new_args
    
    intervals = new_args['profit_intervals']
    lst = []
    for interval in intervals:
        interval_list = interval.split('-')
        start_interval = datetime.strptime(interval_list[0], "%Y%m%d")
        end_interval = datetime.strptime(interval_list[1], "%Y%m%d")
        lst.append((start_interval, end_interval))
    new_args['profit_intervals'] = lst
    return new_args

def construct_parser():
    parser = argparse.ArgumentParser(description="Compute tax implications from stock sale")
    parser.add_argument("--txn_file", help="Transaction Csv file path", required=True)
    parser.add_argument("--metadata_file", help="Metadata Csv file", required=True)
    parser.add_argument("--fy_year", help="FY Year e.g. 2019-2020", required=True)
    parser.add_argument("--output_file", help="Output File")
    parser.add_argument("--profit_intervals", nargs="+", help="Profit intervals")
    parser.add_argument("--cii_file", help="CII Table", required=True)
    return parser

def parse_args():
    parser = construct_parser()
    args = vars(parser.parse_args())
    args = preprocess_args(args)
    return args

def validate_input(args):
    # Validate Transaction dataframe
    txn_df = pd.read_csv(args["txn_file"])
    txn_col_names = ['Entity', 'Units', 'Price', 'Date']
    validate_df('Transaction', txn_df, txn_col_names)
    
    metadata_df = pd.read_csv(args["metadata_file"])
    metadata_col_names = ['Entity', 'LongTermDays', 'FundType']
    validate_df('Metadata', metadata_df, metadata_col_names)

    cii_df = pd.read_csv(args["cii_file"])
    cii_col_names = ['FYYear', 'CII']
    validate_df('CII Table', cii_df, cii_col_names)

def validate_df(csv_name, df, expected_cols):
    diff = set(expected_cols) - set(df.columns)
    if diff:
        raise ValueError("{0} CSV doesn't have the following columns: {1}".format(csv_name, str(diff)))

if __name__ == "__main__":
    args = parse_args()
    validate_input(args)
    txn_df = compute_txn_df(args)
    if 'output_file' in args:
        txn_df.to_csv(args['output_file'], float_format='%.2f')

    if 'profit_intervals' in args:
        profit_summary = compute_profit_summary(txn_df, args['profit_intervals'])
        for k, v in profit_summary.items():
            print("{0}-{1} -> {2}".format(k[0].strftime("%Y%m%d"), k[1].strftime("%Y%m%d"), v))