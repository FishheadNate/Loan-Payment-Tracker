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
import pprint

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger()

date_format = '%m-%d-%Y'


def run(args):
    loan_amount = args.amount
    interest_rate_annual = args.interest
    term_length_months = args.length
    origination_date = datetime.strptime(args.origination_date, date_format)

    amortization_json = calculate_amortization(origination_date, loan_amount, interest_rate_annual, term_length_months)

    if args.balloon_month:
        apply_balloon_payment(amortization_json, args.balloon_month)

    output = 'Amortization-Table-' + str(term_length_months) + 'months.csv'
    logging.info('Exporting table to: ' + output)
    export_amortization_csv(amortization_json, interest_rate_annual, output)


def export_amortization_csv(amortization_json, interest_rate_annual, output):
    interest_col = 'Interest (' + str(interest_rate_annual * 100) + '% APR)'
    with open(output, 'w', newline='') as dst_file:
        fieldnames = [
            'Payment Number',
            'Payment Date',
            'Beginning Balance',
            'Scheduled Payment',
            'Extra Payment',
            'Total Payment',
            'Principal',
            interest_col,
            'Ending Balance'
        ]
        writer = csv.DictWriter(dst_file, fieldnames=fieldnames)
        writer.writeheader()
        for i in list(amortization_json.keys()):
            if amortization_json[i]["Extra Payment"] is None:
                extra_payment = 0
                total_payment = amortization_json[i]["Amount Due"]
            else:
                extra_payment = amortization_json[i]["Extra Payment"]
                total_payment = amortization_json[i]["Amount Due"] + extra_payment
            writer.writerow({
                "Payment Number": i,
                "Payment Date": amortization_json[i]["Due Date"],
                "Beginning Balance": "${:,.2f}".format(amortization_json[i]["Start Balance"]),
                "Scheduled Payment": "${:,.2f}".format(amortization_json[i]["Amount Due"]),
                "Extra Payment": "${:,.2f}".format(extra_payment),
                "Total Payment": "${:,.2f}".format(total_payment),
                "Principal": "${:,.2f}".format(amortization_json[i]["Principal Due"]),
                interest_col: "${:,.2f}".format(amortization_json[i]["Interest Due"]),
                "Ending Balance": "${:,.2f}".format(amortization_json[i]["End Balance"])
            })


def apply_balloon_payment(amortization_json, balloon_month):
    logging.info('Applying a balloon payment to term month number: ' + str(balloon_month))
    for m in list(amortization_json.keys()):
        if m < balloon_month:
            amortization_json[m]["Extra Payment"] = 0
        elif m == balloon_month:
            start_balance = amortization_json[m - 1]["Start Balance"]
            current_interest = amortization_json[m]["Interest Due"]
            current_payment_due = amortization_json[m]["Amount Due"]

            payoff_amount = start_balance + current_interest
            extra_payment = payoff_amount - current_payment_due
            end_balance = payoff_amount - current_payment_due - extra_payment

            amortization_json[m]["Extra Payment"] = round(extra_payment, 2)
            amortization_json[m]["End Balance"] = round(end_balance, 2)
        else:
            amortization_json[m]["Start Balance"] = 0
            amortization_json[m]["Amount Due"] = 0
            amortization_json[m]["Extra Payment"] = 0
            amortization_json[m]["Total Payment"] = 0
            amortization_json[m]["Principal Due"] = 0
            amortization_json[m]["Interest Due"] = 0
            amortization_json[m]["End Balance"] = 0


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
            ("Extra Payment", None),
            ("Total Payment", None),
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
    parser.add_argument('--amount', help='Total loan amount (XXXXX.XX)', dest='amount', type=float, required=True)
    parser.add_argument('--interest', help='Annual interest rate (X.XX)', dest='interest', type=float, required=True)
    parser.add_argument('--length', help='Term length of the loan in months', dest='length', type=int, required=True)
    parser.add_argument('--origin_date', help='Loan origination date (MM-DD-YYYY)', dest='origination_date', required=True)
    parser.add_argument('--balloon_month', help='Term month on which to apply a balloon payment', dest='balloon_month', type=int, required=False)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()