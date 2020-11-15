"""
<ITRForm:Schedule112A>
                        <ITRForm:Schedule112ADtls>
                            <ITRForm:ShareOnOrBefore>AE</ITRForm:ShareOnOrBefore>
                                <ITRForm:ISINCode>INNOTREQUIRD</ITRForm:ISINCode>
                                <ITRForm:ShareUnitName>CONSOLIDATED</ITRForm:ShareUnitName>
                                <ITRForm:NumSharesUnits>0</ITRForm:NumSharesUnits>
                                <ITRForm:SalePricePerShareUnit>0</ITRForm:SalePricePerShareUnit>
                                <ITRForm:TotSaleValue>2349.38</ITRForm:TotSaleValue>
                                <ITRForm:CostAcqWithoutIndx>2000.0000</ITRForm:CostAcqWithoutIndx>
                                <ITRForm:AcquisitionCost>2000</ITRForm:AcquisitionCost>
                                <ITRForm:LTCGBeforelowerB1B2>0.0000</ITRForm:LTCGBeforelowerB1B2>
                                <ITRForm:FairMktValuePerShareunit>0</ITRForm:FairMktValuePerShareunit>
                                <ITRForm:TotFairMktValueCapAst>0.0000</ITRForm:TotFairMktValueCapAst>
                                <ITRForm:ExpExclCnctTransfer/>
                                <ITRForm:TotalDeductions>2000.0000</ITRForm:TotalDeductions>
                                <ITRForm:Balance>349.3800</ITRForm:Balance>
                        </ITRForm:Schedule112ADtls>
"""
import pandas as pd
import xml.etree.ElementTree as ET
import argparse
from datetime import datetime
"""
CSV column separator: ","
CSV columns expected:
<Entity>: Name of MF/Equity
<Units>: Units purchased. Should be negative if units are sold
<Price>: Price at which the units were purchased/sold. Must be positive
<Date>: Transaction Date, format: dd-mon-yyyy e.g. 01-Jan-1990
"""
parser = argparse.ArgumentParser(description="Compute tax implications from stock sale")
parser.add_argument("--gains_file", help="Gains Csv file path", required=True)
parser.add_argument("--income_tax_file", help="Tax Xml file that is to be read", required=True)
parser.add_argument("--output_file", help="The output file that's to be written to")
args = vars(parser.parse_args())
float_formatter = "{:.2f}"

gains_df = pd.read_csv(args['gains_file'])
tree = ET.parse(args['income_tax_file'])
root = tree.getroot()
namespace = "{http://incometaxindiaefiling.gov.in/master}"
ET.register_namespace("ITRForm", namespace)
qname = ET.QName(namespace, "Schedule112A")
node = ET.Element(qname)
for index, row in gains_df.iterrows():
    qname = ET.QName(namespace, "Schedule112ADtls")
    elem = ET.Element(qname)

    qname = ET.QName(namespace, "ShareOnOrBefore")
    share_on_or_before = ET.Element(qname)
    share_on_or_before.text = "AE"
    elem.append(share_on_or_before)

    qname = ET.QName(namespace, "ISINCode")
    isin_code = ET.Element(qname)
    isin_code.text = "INNOTREQUIRD"
    elem.append(isin_code)

    
    qname = ET.QName(namespace, "ShareUnitName")
    share_unit_name = ET.Element(qname)
    share_unit_name.text = "CONSOLIDATED"
    elem.append(share_unit_name)

    qname = ET.QName(namespace, "NumSharesUnits")
    num_shares = ET.Element(qname)
    num_shares.text = float_formatter.format(row.Units)
    elem.append(num_shares)

    qname = ET.QName(namespace, "SalePricePerShareUnit")
    sale_price_per_share_unit = ET.Element(qname)
    sale_price_per_share_unit.text = float_formatter.format(row.SalePrice)
    elem.append(sale_price_per_share_unit)

    qname = ET.QName(namespace, "TotSaleValue")
    total_sale_value = ET.Element(qname)
    total_sale_value.text = float_formatter.format(int(row.SalePrice * 100) * int(row.Units * 100)/(10000.0))
    elem.append(total_sale_value)

    qname = ET.QName(namespace, "CostAcqWithoutIndx")
    cost_acquisition_without_idx = ET.Element(qname)
    cost_acquisition_without_idx.text = float_formatter.format(row.CostOfAcquisition)
    elem.append(cost_acquisition_without_idx)

    qname = ET.QName(namespace, "AcquisitionCost")
    acquisition_cost = ET.Element(qname)
    acquisition_cost.text = float_formatter.format(row.CostOfAcquisition)
    elem.append(acquisition_cost)

    qname = ET.QName(namespace, "LTCGBeforelowerB1B2")
    ltcg_before_lower_b1b2 = ET.Element(qname)
    ltcg_before_lower_b1b2.text = "0.0000"
    elem.append(ltcg_before_lower_b1b2)

    qname = ET.QName(namespace, "FairMktValuePerShareunit")
    fair_mkt_value = ET.Element(qname)
    fair_mkt_value.text = "0"
    elem.append(fair_mkt_value)

    
    qname = ET.QName(namespace, "TotFairMktValueCapAst")
    total_fair_mkt_val_cap_ast = ET.Element(qname)
    total_fair_mkt_val_cap_ast.text = "0.0000"
    elem.append(total_fair_mkt_val_cap_ast)

    qname = ET.QName(namespace, "ExpExclCnctTransfer")
    transfer_cost = ET.Element(qname)
    transfer_cost.text = "0"
    elem.append(transfer_cost)
    
    qname = ET.QName(namespace, "TotalDeductions")
    total_deductions = ET.Element(qname)
    total_deductions.text = float_formatter.format(row.CostOfAcquisition)
    elem.append(total_deductions)
    
    qname = ET.QName(namespace, "Balance")
    balance = ET.Element(qname)
    balance.text = float_formatter.format(row.FairValue - row.CostOfAcquisition)
    elem.append(balance)

    node.append(elem)

tree = ET.ElementTree()
tree._setroot(node)
tree.write(args['output_file'])
