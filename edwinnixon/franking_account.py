"""
Franking account ledger, balance tracking, and Franking Deficit Tax (FDT) calculations
under Part 3-6 (Divisions 205 and 214) of the Income Tax Assessment Act 1997.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional


class FrankingEntryType(str, Enum):
    # Credits (s 205-15)
    PAYG_INSTALMENT = "PAYG_INSTALMENT"             # Item 1: Payment of PAYG instalment
    COMPANY_TAX_PAYMENT = "COMPANY_TAX_PAYMENT"     # Item 2: Payment of company tax assessment
    FRANKED_DISTRIBUTION_REC = "FRANKED_DIST_REC"   # Item 3: Receipt of franked distribution

    # Debits (s 205-30)
    FRANKED_DISTRIBUTION_PAID = "FRANKED_DIST_PAID" # Item 1: Franked distribution made
    TAX_REFUND = "TAX_REFUND"                       # Item 2: Receipt of tax refund
    OVER_FRANKING_TAX = "OVER_FRANKING_TAX"         # Item 3: Debit arising from over-franking


@dataclass(frozen=True)
class FrankingEntry:
    entry_date: date
    entry_type: FrankingEntryType
    amount: Decimal
    description: str
    statutory_reference: str = ""

    @property
    def is_credit(self) -> bool:
        return self.entry_type in {
            FrankingEntryType.PAYG_INSTALMENT,
            FrankingEntryType.COMPANY_TAX_PAYMENT,
            FrankingEntryType.FRANKED_DISTRIBUTION_REC,
        }

    @property
    def is_debit(self) -> bool:
        return not self.is_credit


@dataclass(frozen=True)
class FrankingDeficitResult:
    closing_balance: Decimal
    has_deficit: bool
    franking_deficit_tax: Decimal
    total_franking_credits_year: Decimal
    fdt_offset_reduction_applies: bool
    allowable_tax_offset: Decimal
    statutory_basis: str


@dataclass
class FrankingAccount:
    financial_year: int
    opening_balance: Decimal = Decimal("0.00")
    entries: List[FrankingEntry] = field(default_factory=list)

    def record_payg_instalment(self, entry_date: date, amount: Decimal, description: str = "PAYG instalment paid") -> FrankingEntry:
        entry = FrankingEntry(
            entry_date=entry_date,
            entry_type=FrankingEntryType.PAYG_INSTALMENT,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            description=description,
            statutory_reference="s 205-15 Item 1 ITAA 1997",
        )
        self.entries.append(entry)
        return entry

    def record_tax_assessment_paid(self, entry_date: date, amount: Decimal, description: str = "Company tax assessment paid") -> FrankingEntry:
        entry = FrankingEntry(
            entry_date=entry_date,
            entry_type=FrankingEntryType.COMPANY_TAX_PAYMENT,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            description=description,
            statutory_reference="s 205-15 Item 2 ITAA 1997",
        )
        self.entries.append(entry)
        return entry

    def record_franked_distribution_received(self, entry_date: date, franking_credit: Decimal, description: str = "Franked dividend received") -> FrankingEntry:
        entry = FrankingEntry(
            entry_date=entry_date,
            entry_type=FrankingEntryType.FRANKED_DISTRIBUTION_REC,
            amount=franking_credit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            description=description,
            statutory_reference="s 205-15 Item 3 ITAA 1997",
        )
        self.entries.append(entry)
        return entry

    def record_franked_distribution_paid(self, entry_date: date, franking_credit_attached: Decimal, description: str = "Franked dividend paid") -> FrankingEntry:
        entry = FrankingEntry(
            entry_date=entry_date,
            entry_type=FrankingEntryType.FRANKED_DISTRIBUTION_PAID,
            amount=franking_credit_attached.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            description=description,
            statutory_reference="s 205-30 Item 1 ITAA 1997",
        )
        self.entries.append(entry)
        return entry

    def record_tax_refund(self, entry_date: date, refund_amount: Decimal, description: str = "Income tax refund received") -> FrankingEntry:
        entry = FrankingEntry(
            entry_date=entry_date,
            entry_type=FrankingEntryType.TAX_REFUND,
            amount=refund_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            description=description,
            statutory_reference="s 205-30 Item 2 ITAA 1997",
        )
        self.entries.append(entry)
        return entry

    @property
    def total_credits(self) -> Decimal:
        return sum((e.amount for e in self.entries if e.is_credit), Decimal("0.00"))

    @property
    def total_debits(self) -> Decimal:
        return sum((e.amount for e in self.entries if e.is_debit), Decimal("0.00"))

    @property
    def closing_balance(self) -> Decimal:
        return (self.opening_balance + self.total_credits - self.total_debits).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def evaluate_franking_deficit(self) -> FrankingDeficitResult:
        """
        Evaluate Franking Deficit Tax (FDT) under s 205-45 and tax offset under s 205-70.
        If the franking deficit exceeds 10% of total franking credits generated in the year,
        the tax offset is reduced by 30% (s 205-70(6)).
        """
        balance = self.closing_balance
        if balance >= Decimal("0.00"):
            return FrankingDeficitResult(
                closing_balance=balance,
                has_deficit=False,
                franking_deficit_tax=Decimal("0.00"),
                total_franking_credits_year=self.total_credits,
                fdt_offset_reduction_applies=False,
                allowable_tax_offset=Decimal("0.00"),
                statutory_basis="s 205-45 ITAA 1997: Surplus franking account balance; no FDT liability.",
            )

        fdt = abs(balance)
        credits_year = self.total_credits
        threshold = credits_year * Decimal("0.10")

        # Check 10% threshold rule (s 205-70(6))
        reduction_applies = credits_year > Decimal("0.00") and (fdt > threshold)

        if reduction_applies:
            # 30% reduction penalty
            offset = (fdt * Decimal("0.70")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            basis = (
                f"s 205-45 ITAA 1997: FDT liability ${fdt:,.2f}. Deficit exceeds 10% of total credits "
                f"(${credits_year:,.2f}); tax offset is reduced by 30% to ${offset:,.2f} under s 205-70(6)."
            )
        else:
            offset = fdt
            basis = f"s 205-45 ITAA 1997: FDT liability ${fdt:,.2f}. 100% allowable as tax offset under s 205-70."

        return FrankingDeficitResult(
            closing_balance=balance,
            has_deficit=True,
            franking_deficit_tax=fdt,
            total_franking_credits_year=credits_year,
            fdt_offset_reduction_applies=reduction_applies,
            allowable_tax_offset=offset,
            statutory_basis=basis,
        )