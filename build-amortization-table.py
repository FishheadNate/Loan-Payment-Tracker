#!/usr/bin/env python3
############################################
# Builds an amortization table based on the
# total loan amount, interest rate, & the
# duration of the loan.
############################################
import argparse
import csv
import logging
import numpy_financial as npf
from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger()

date_format = '%m-%d-%Y'


def run(args):
    loan_amount = args.amount
    interest_rate_annual = args.interest
    term_length_months = args.length
    origination_date = datetime.strptime(args.origination_date, date_format)

    amortization_json = calculate_amortization(origination_date, loan_amount, interest_rate_annual, term_length_months)

    output = 'Amortization-Table-' + str(term_length_months) + 'months.csv'
    logging.info('Exporting table to: ' + output)
    export_amortization_csv(amortization_json, interest_rate_annual, output)


def export_amortization_csv(amortization_json, interest_rate_annual, output):
    interest_col = 'Interest (' + str(interest_rate_annual * 100) + '% APR)'
    with open(output, 'w', newline='') as dst_file:
        fieldnames = [
            'Payment Number',
            'Due Date',
            'Starting Balance',
            'Total Due',
            'Principal',
            interest_col,
            'Ending Balance'
        ]
        writer = csv.DictWriter(dst_file, fieldnames=fieldnames)
        writer.writeheader()
        for i in list(amortization_json.keys()):
            writer.writerow({
                "Payment Number": i,
                "Due Date": amortization_json[i]["Due Date"],
                "Starting Balance": "${:,.2f}".format(amortization_json[i]["Start Balance"]),
                "Total Due": "${:,.2f}".format(amortization_json[i]["Amount Due"]),
                "Principal": "${:,.2f}".format(amortization_json[i]["Principal Due"]),
                interest_col: "${:,.2f}".format(amortization_json[i]["Interest Due"]),
                "Ending Balance": "${:,.2f}".format(amortization_json[i]["End Balance"])
            })


def calculate_amortization(origination_date, loan_amount, interest_rate_annual, term_length_months):
    amortization_json = {}
    interest_rate_monthly = interest_rate_annual / 12
    payments_start_date = origination_date + relativedelta(months=1)

    logging.info('Building list of payment due dates')
    due_dates = list_due_dates(payments_start_date, payments_start_date + relativedelta(months=term_length_months))

    logging.info('Calculating Principal & Interest')
    for term_month in range(1, term_length_months + 1):
        monthly_payment_amount = npf.pmt(interest_rate_monthly, term_length_months, - loan_amount)
        monthly_interest_payment = npf.ipmt(interest_rate_monthly, term_month, term_length_months, - loan_amount)
        monthly_principal_payment = npf.ppmt(interest_rate_monthly, term_month, term_length_months, - loan_amount)

        principal_due = round(float(monthly_principal_payment), 3)
        interest_due = round(float(monthly_interest_payment), 3)
        amount_due = round(float(monthly_payment_amount), 2)

        if term_month == 1:
            start_balance = loan_amount
        else:
            start_balance = None

        amortization_json[term_month] = OrderedDict([
            ("Start Balance", start_balance),
            ("Due Date", due_dates[term_month - 1]),
            ("Amount Due", amount_due),
            ("Principal Due", principal_due),
            ("Interest Due", interest_due),
            ("End Balance", None)
        ])

    logging.info('Calculating Running Balance')
    for m in list(amortization_json.keys()):
        current_principal = amortization_json[m]["Principal Due"]

        if amortization_json[m]["Start Balance"] == loan_amount and amortization_json[m]["End Balance"] is None:
            end_balance = loan_amount - current_principal

            amortization_json[m]["End Balance"] = round(end_balance, 2)

        if amortization_json[m]["Start Balance"] is None and amortization_json[m]["End Balance"] is None:
            previous_month_end_balance = amortization_json[m - 1]["End Balance"]
            end_balance = previous_month_end_balance - current_principal

            amortization_json[m]["Start Balance"] = previous_month_end_balance

            if previous_month_end_balance < amortization_json[m]["Amount Due"]:
                amortization_json[m]["End Balance"] = round(end_balance, 1)
            else:
                amortization_json[m]["End Balance"] = round(end_balance, 2)

    return amortization_json


def list_due_dates(start_date, end_date):
    due_by_delta = timedelta(days=7, hours=12)

    start = start_date + due_by_delta
    end = end_date + due_by_delta
    delta = timedelta(days=1)

    due_dates_list = []

    while start <= end:
        if start.day == 10:
            due_dates_list.append(start.strftime("%B %d, %Y"))
        start += delta

    return due_dates_list


def main():
    parser = argparse.ArgumentParser(description='Tracks loan payments and exports a receipt')
    parser.add_argument('-amount', help='Total loan amount (XXXXX.XX)', dest='amount', type=float, required=True)
    parser.add_argument('-interest', help='Annual interest rate (X.XX)', dest='interest', type=float, required=True)
    parser.add_argument('-length', help='Term length of the loan in months', dest='length', type=int, required=True)
    parser.add_argument('-origin_date', help='Loan origination date (MM-DD-YYYY)', dest='origination_date', required=True)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()