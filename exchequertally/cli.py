"""
CLI interface for TheExchequerTally.
"""

import argparse
import sys
from datetime import date
from decimal import Decimal
from .corporate_tax import BaseRateEntityTest, determine_corporate_tax_rate
from .franking_account import FrankingAccount
from .distribution_statement import generate_distribution_statement


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="frank-check",
        description="TheExchequerTally: Corporate Tax Rate & Franking Account Engine for Australian Companies",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: bre-test
    bre_parser = subparsers.add_parser("bre-test", help="Test Base Rate Entity (BRE) eligibility under s 23AA ITRA 1986")
    bre_parser.add_argument("--fy", type=int, required=True, help="Financial Year ending (e.g. 2025)")
    bre_parser.add_argument("--turnover", type=Decimal, required=True, help="Aggregated turnover ($)")
    bre_parser.add_argument("--assessable", type=Decimal, required=True, help="Total assessable income ($)")
    bre_parser.add_argument("--passive", type=Decimal, required=True, help="Base Rate Entity Passive Income ($)")

    # Command: dist-statement
    dist_parser = subparsers.add_parser("dist-statement", help="Generate distribution statement details")
    dist_parser.add_argument("--entity", type=str, required=True, help="Company name")
    dist_parser.add_argument("--acn", type=str, required=True, help="ACN or ABN")
    dist_parser.add_argument("--recipient", type=str, required=True, help="Shareholder name")
    dist_parser.add_argument("--amount", type=Decimal, required=True, help="Total dividend distribution ($)")
    dist_parser.add_argument("--franking-pct", type=Decimal, default=Decimal("100.00"), help="Franking percentage (e.g. 100)")
    dist_parser.add_argument("--tax-rate", type=Decimal, default=Decimal("0.25"), help="Corporate tax rate (0.25 or 0.30)")

    args = parser.parse_args()

    if args.command == "bre-test":
        test = BaseRateEntityTest(
            financial_year=args.fy,
            aggregated_turnover=args.turnover,
            assessable_income=args.assessable,
            passive_income=args.passive,
        )
        res = determine_corporate_tax_rate(test)
        print("=" * 60)
        print(f"Base Rate Entity (BRE) Evaluation — FY{args.fy}")
        print("=" * 60)
        print(f"Aggregated Turnover:     ${args.turnover:,.2f} (< $50M: {test.is_aggregated_turnover_eligible})")
        print(f"Passive Income Ratio:    {test.passive_income_percentage:.2f}% (<= 80%: {test.is_brepi_eligible})")
        print(f"Base Rate Entity:        {res.is_base_rate_entity}")
        print(f"Applicable Tax Rate:     {res.applicable_rate * 100:.1f}%")
        print(f"Statutory Basis:         {res.statutory_basis}")
        print("=" * 60)
        return 0

    elif args.command == "dist-statement":
        stmt = generate_distribution_statement(
            entity_name=args.entity,
            abn_or_acn=args.acn,
            recipient_name=args.recipient,
            payment_date=date.today(),
            total_distribution=args.amount,
            franking_percentage=args.franking_pct,
            corporate_tax_rate=args.tax_rate,
        )
        print("=" * 60)
        print(f"Australian Dividend Distribution Statement — {stmt.entity_name}")
        print("=" * 60)
        print(f"Recipient:               {stmt.recipient_name}")
        print(f"Payment Date:            {stmt.payment_date.isoformat()}")
        print(f"Franked Dividend Amount: ${stmt.franked_amount:,.2f}")
        print(f"Unfranked Amount:        ${stmt.unfranked_amount:,.2f}")
        print(f"Franking Credit:         ${stmt.franking_credit:,.2f}")
        print(f"Franking Percentage:     {stmt.franking_percentage:.2f}%")
        print(f"Gross Assessable:        ${stmt.gross_assessable_income:,.2f}")
        print("=" * 60)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
