"""
Division 203 Benchmark Rule compliance under Sections 203-25 to 203-55 of the ITAA 1997.
Ensures all frankable distributions within a franking period bear the same franking percentage.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class DistributionEvent:
    event_date: date
    recipient_name: str
    distribution_amount: Decimal  # Cash/asset distribution value (unfranked + franked net)
    franking_credit: Decimal
    corporate_tax_rate: Decimal = Decimal("0.25")

    @property
    def franking_percentage(self) -> Decimal:
        """
        Calculate actual franking percentage (s 203-35).
        Franking percentage = (franking credit attached) / (maximum franking credit possible) * 100
        Maximum franking credit = distribution_amount * (tax_rate / (1 - tax_rate))
        """
        if self.distribution_amount <= Decimal("0.00"):
            return Decimal("0.00")

        max_credit = self.distribution_amount * (self.corporate_tax_rate / (Decimal("1.00") - self.corporate_tax_rate))
        if max_credit <= Decimal("0.00"):
            return Decimal("0.00")

        pct = (self.franking_credit / max_credit) * Decimal("100.00")
        return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BenchmarkRuleViolation:
    event_date: date
    recipient_name: str
    benchmark_percentage: Decimal
    actual_percentage: Decimal
    variance_percentage: Decimal
    consequence_type: str  # "OVER_FRANKING_TAX" or "FRANKING_DEBIT"
    penalty_or_debit_amount: Decimal
    statutory_reference: str


class BenchmarkRuleValidator:
    """
    Validates distributions across a franking period against the benchmark franking percentage (s 203-25).
    """
    def __init__(self, corporate_tax_rate: Decimal = Decimal("0.25")):
        self.corporate_tax_rate = corporate_tax_rate
        self.distributions: List[DistributionEvent] = []

    def add_distribution(self, event: DistributionEvent) -> None:
        self.distributions.append(event)

    @property
    def benchmark_percentage(self) -> Optional[Decimal]:
        """
        The benchmark percentage is set by the first frankable distribution in the period (s 203-30).
        """
        if not self.distributions:
            return None
        return self.distributions[0].franking_percentage

    def validate_distributions(self) -> Tuple[bool, List[BenchmarkRuleViolation]]:
        """
        Check all subsequent distributions against the established benchmark percentage.
        """
        if not self.distributions:
            return True, []

        benchmark_pct = self.benchmark_percentage
        violations: List[BenchmarkRuleViolation] = []

        for dist in self.distributions[1:]:
            actual_pct = dist.franking_percentage
            diff = actual_pct - benchmark_pct

            if abs(diff) > Decimal("0.01"):
                max_credit = dist.distribution_amount * (self.corporate_tax_rate / (Decimal("1.00") - self.corporate_tax_rate))
                benchmark_credit = (benchmark_pct / Decimal("100.00")) * max_credit

                if diff > Decimal("0.00"):
                    # Over-franking tax applies (s 203-50(1))
                    over_credit = dist.franking_credit - benchmark_credit
                    violations.append(
                        BenchmarkRuleViolation(
                            event_date=dist.event_date,
                            recipient_name=dist.recipient_name,
                            benchmark_percentage=benchmark_pct,
                            actual_percentage=actual_pct,
                            variance_percentage=diff,
                            consequence_type="OVER_FRANKING_TAX",
                            penalty_or_debit_amount=over_credit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                            statutory_reference="s 203-50(1) ITAA 1997: Over-franking tax payable on excess franking credits.",
                        )
                    )
                else:
                    # Franking debit arises (s 203-50(2))
                    under_debit = benchmark_credit - dist.franking_credit
                    violations.append(
                        BenchmarkRuleViolation(
                            event_date=dist.event_date,
                            recipient_name=dist.recipient_name,
                            benchmark_percentage=benchmark_pct,
                            actual_percentage=actual_pct,
                            variance_percentage=diff,
                            consequence_type="FRANKING_DEBIT",
                            penalty_or_debit_amount=under_debit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                            statutory_reference="s 203-50(2) ITAA 1997: Franking account debit arises equal to shortfall.",
                        )
                    )

        return len(violations) == 0, violations