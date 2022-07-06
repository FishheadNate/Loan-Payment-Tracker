#!/usr/bin/env python3
#############################################
# Tracks payments received, late fees, and
# updates a CSV of the payment history. Runs
# an external script to export a PDF receipt.
#############################################
import argparse
import csv
import logging
import re
from collections import OrderedDict
from datetime import datetime
from re import sub

import create_receipt_pdf

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger()


def run(args):
    date_format = '%m-%d-%Y'
    amortization_table = csv.DictReader(open(args.amortization))
    payments_csv = 'payments.csv'
    record_of_payments = csv.DictReader(open(payments_csv))

    payment = OrderedDict([
        ("Payment Number", payment_number(record_of_payments)),
        ("Received Amount", args.collected),
        ("Received Date", datetime.strptime(args.collected_date, date_format)),
        ("Check Number", args.check_num),
        ("Notes", args.notes),
    ])

    logging.info(
        'Processing payment of $' + str(payment["Received Amount"])
        + ' received on ' + payment["Received Date"].strftime('%B %d, %Y'))

    amortization_data = read_amortization_table(amortization_table)

    payment_update = apply_payment(payment, amortization_data)

    update_record_of_payments(payments_csv, payment_update)


def update_record_of_payments(payments_csv, payment_update):
    with open(payments_csv, 'a') as dst_file:
        csvwriter = csv.writer(dst_file)
        csvwriter.writerow(dict(payment_update).values())
        dst_file.close()

    logging.info(payments_csv + ' has been updated')


def apply_payment(payment, amortization_data):
    payment_number = payment["Payment Number"]
    start_balance = amortization_data[payment_number]["Starting Balance"]
    amount_due = amortization_data[payment_number]["Amount Due"]
    amount_received = payment["Received Amount"]
    principal_due = amortization_data[payment_number]["Principal"]
    interest_due = amortization_data[payment_number]["Interest"]

    logging.info('Starting balance: ' + "${:,.2f}".format(start_balance))
    if amount_received == amount_due:
        end_balance = amortization_data[payment_number]["Ending Balance"]

    if amount_received > amount_due or amount_received > interest_due:
        remove_interest_due = amount_received - interest_due
        end_balance = start_balance - remove_interest_due

    if amount_received < amount_due:
        if amount_received == interest_due:
            end_balance = start_balance
        else:
            remaining_amount = amount_received - interest_due
            if remaining_amount > 0:
                end_balance = start_balance - remaining_amount
                logging.info(
                    "${:,.2f}".format(principal_due - remaining_amount)
                    + ' of unpaid principal needs to be added to the next invoice'
                )
            else:
                end_balance = start_balance
                logging.info(
                    "${:,.2f}".format(abs(remaining_amount))
                    + ' of interest was left unpaid'
                )
    logging.info('Ending balance: ' + "${:,.2f}".format(end_balance))

    days_late = (payment["Received Date"] - amortization_data[payment_number]["Due Date"]).days
    if days_late > 0:
        late_fee = "${:,.2f}".format(round((principal_due * (18 / 365)) * days_late, 2))
        logging.info('Late Fee: ' + late_fee)
    else:
        days_late = 0
        late_fee = 0

    payment_update = OrderedDict([
        ('Payment Number', payment_number),
        ('Due Date', amortization_data[payment_number]["Due Date"].strftime('%B %d, %Y')),
        ('Received Date', payment["Received Date"].strftime('%B %d, %Y')),
        ('Days Late', days_late),
        ('Check Number', payment["Check Number"]),
        ('Starting Balance', "${:,.2f}".format(amortization_data[payment_number]["Starting Balance"])),
        ('Amount Due', "${:,.2f}".format(amount_due)),
        ('Received Amount', "${:,.2f}".format(amount_received)),
        ('Principal', "${:,.2f}".format(principal_due)),
        ('Interest', "${:,.2f}".format(interest_due)),
        ('Ending Balance', "${:,.2f}".format(end_balance)),
        ('Late Fee', late_fee),
        ('Notes', payment["Notes"])
    ])

    return payment_update


def payment_number(record_of_payments):
        past_payments = []
        for row in record_of_payments:
            past_payments.append(int(row["Payment Number"]))

        if len(past_payments) == 0:
            logging.info('No previous payments have been received')
            current_payment_number = 1
        else:
            current_payment_number = max(past_payments) + 1

        return current_payment_number


def read_amortization_table(amortization_table):
    amortization_data = OrderedDict()
    for row in amortization_table:
        for k in list(row.keys()):
            if k.startswith('Interest'):
                interest_column = k

        amortization_data[int(row["Payment Number"])] = OrderedDict([
            ("Due Date", datetime.strptime(row["Payment Date"], '%B %d, %Y')),
            ("Starting Balance", float(sub(r'[^\d.]', '', row["Beginning Balance"]))),
            ("Amount Due", float(sub(r'[^\d.]', '', row["Scheduled Payment"]))),
            ("Principal", float(sub(r'[^\d.]', '', row["Principal"]))),
            ("Interest", float(sub(r'[^\d.]', '', row[interest_column]))),
            ("Ending Balance", float(sub(r'[^\d.]', '', row["Ending Balance"])))
        ])

    return amortization_data


def main():
    parser = argparse.ArgumentParser(description='Tracks loan payments and exports a receipt')
    parser.add_argument('--amortization_table', help='File path to amortization table', dest='amortization', required=True)
    parser.add_argument('--payment', help='Payment amount received', dest='collected', type=float, required=True)
    parser.add_argument('--date', help='Date of payment (MM-DD-YYYY HH:MMPM)', dest='collected_date', required=True)
    parser.add_argument('--check_numb', help='Check Number or Payment type (ACH, Cash)', dest='check_num', type=int, required=True)
    parser.add_argument('--notes', help='Payment notes', dest='notes', default='', required=True)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
    create_receipt_pdf.run()
