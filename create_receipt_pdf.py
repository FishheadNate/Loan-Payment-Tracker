#!/usr/bin/env python3
#########################################
# Exports a PDF receipt based on the CSV
# output form processing a payment.
######################################
import argparse
import csv
import os
import logging
from datetime import datetime
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger()

record_of_payments = csv.DictReader(open('payments.csv'))

def run():
    payment_json = payment_details(record_of_payments)

    output_page_size = (8.5 * inch, 3.625 * inch)

    run_date = datetime.now().strftime('%m-%d-%Y')

    receipt_template(run_date, payment_json, output_page_size)


def receipt_template(run_date, payment_json, output_page_size):
    '''
    Canvas coordinates (x, y)
        (points from left, points from bottom)
        1 point = 1/72 inch
    '''
    receipt_output = 'receipts/payment_' + run_date +'.pdf'
    canvas = Canvas(receipt_output, pagesize=output_page_size)

    header_font_into = ['Helvetica-Bold', 14]
    title_font_into = ['Helvetica-Bold', 11]
    item_font_into = ['Helvetica', 10]

    #########
    # Footer
    canvas.setLineWidth(0.5)
    canvas.line(36, 36, 576, 36)

    #####################
    # Received Signature
    title_text = 'Received By:'
    title_indent = 72
    title_height = 54
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])
    canvas.line(title_indent + 2 + title_length, title_height - 2, title_indent + title_length + 175, title_height - 2)

    #############
    # Amount Due
    title_text = '              Payment Information              '
    title_indent = 556
    title_height = 189
    canvas.setFont(title_font_into[0], title_font_into[1])
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent - title_length, title_height, title_text)
    canvas.setLineWidth(0.5)
    canvas.line(title_indent - title_length, title_height - 4, title_indent, title_height - 4)

    item_text = 'Principal:'
    item_height = 1 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    item_value = '${:,.2f}'.format(payment_json["principal_due"])
    item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)

    item_text = 'Interest:'
    item_height = 2 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    item_value = '${:,.2f}'.format(payment_json["interest_due"])
    item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)

    item_text = 'Fees:'
    item_height = 3 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    item_value = '${:,.2f}'.format(payment_json["late_fee"])
    item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)

    item_text = 'Total Due:'
    item_height = 4 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    item_value = '${:,.2f}'.format(payment_json["principal_due"] + payment_json["interest_due"])
    item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)
    canvas.line(title_indent - 9 - item_value_length, title_height - item_height + 13, title_indent - 3, title_height - item_height + 13)

    item_text = 'Paid:'
    item_height = 5 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    item_value = '- ${:,.2f}'.format(payment_json["payment_amount"])
    item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)
    canvas.line(title_indent - 9 - item_value_length, title_height - item_height - 6, title_indent - 3, title_height - item_height - 6)

    item_text = 'Extra Principal Payment:'
    item_height = 6 * 18
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent - title_length + 6, title_height - item_height, item_text)

    extra_principal_payment = payment_json["payment_amount"] - payment_json["principal_due"] - payment_json["interest_due"]
    if extra_principal_payment > 0:
        item_value = '${:,.2f}'.format(extra_principal_payment)
        item_value_length = canvas.stringWidth(item_value, item_font_into[0], item_font_into[1])
        canvas.drawString(title_indent - 6 - item_value_length, title_height - item_height, item_value)

    ##################
    # Payment Method
    title_text = 'Payment Method:'
    title_indent = 72
    title_height = 99
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])

    if payment_json["payment_type"] == 'check':
        item_text = '  Check [X]   ACH [  ]   Cash [  ]'
    elif payment_json["payment_type"] == 'ach':
        item_text = '  Check [  ]   ACH [X]   Cash [  ]'
    elif payment_json["payment_type"] == 'cash':
        item_text = '  Check [  ]   ACH [  ]   Cash [X]'
    else:
        logging.info('Unknown payment method')
        item_text = '  Check [  ]   ACH [  ]   Cash [  ]'
    canvas.setFont(item_font_into[0], item_font_into[1])
    canvas.drawString(title_indent + title_length, title_height, item_text)

    ###############
    # Amount Paid
    title_text = 'Amount Paid:'
    title_indent = 72
    title_height = 117
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])

    item_value = '${:,.2f}'.format(payment_json["payment_amount"])
    canvas.setFont(item_font_into[0], 12)
    canvas.drawString(title_indent + title_length + 4, title_height, item_value)

    ###############
    # Due Date
    title_text = 'Date Received:'
    title_indent = 72
    title_height = 135
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])

    item_value = str(payment_json["payment_date"])
    canvas.setFont(item_font_into[0], 12)
    canvas.drawString(title_indent + title_length + 4, title_height, item_value)

    ###############
    # Payment Date
    title_text = 'Payment Due:'
    title_indent = 72
    title_height = 153
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])

    item_value = str(payment_json["due_date"])
    canvas.setFont(item_font_into[0], 12)
    canvas.drawString(title_indent + title_length + 4, title_height, item_value)

    #################
    # Payment Number
    title_text = 'Payment Number:'
    title_indent = 72
    title_height = 171
    canvas.setFont(title_font_into[0], title_font_into[1])
    canvas.drawString(title_indent, title_height, title_text)
    title_length = canvas.stringWidth(title_text, title_font_into[0], title_font_into[1])

    item_value = str(payment_json["payment_number"])
    canvas.setFont(item_font_into[0], 12)
    canvas.drawString(title_indent + title_length + 4, title_height, item_value)

    #########
    # Header
    header_text = 'Payment Receipt'
    header_indent = 72
    header_height = 225
    canvas.setFont(header_font_into[0], header_font_into[1])
    canvas.drawString(header_indent, header_height, header_text)
    canvas.setLineWidth(0.5)
    canvas.line(36, header_height - 6, 576, header_height - 6)
    canvas.line(36, header_height + 14, 576, header_height + 14)





    canvas.save()


def payment_details(record_of_payments):
    latest_payment = list(record_of_payments)[-1]

    payment_json = {
        "principal_due": float(latest_payment["Principal"].strip('$')),
        "interest_due": float(latest_payment["Interest"].strip('$')),
        "payment_amount": float(latest_payment["Received Amount"].strip('$')),
        "payment_date": latest_payment["Received Date"],
        "late_fee": float(latest_payment["Late Fee"].strip('$')),
        "payment_number": int(latest_payment["Payment Number"]),
        "due_date": latest_payment["Due Date"]
    }

    if isinstance(int(latest_payment["Check Number"]),int):
        payment_json["payment_type"] = 'check'
    elif latest_payment["Check Number"].lower() == 'ach':
        payment_json["payment_type"] = 'ach'
    elif latest_payment["Check Number"].lower() == 'cash':
        payment_json["payment_type"] = 'cash'
    else:
        payment_json["payment_type"] = 'unknown'

    return payment_json


def main():
    parser = argparse.ArgumentParser(description='Exports a PDF receipt')
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func()


if __name__ == '__main__':
    main()