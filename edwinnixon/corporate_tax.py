"""
Corporate tax rate determination and Base Rate Entity (BRE) test under
Sections 23AA & 23AB of the Income Tax Rates Act 1986 and Division 328 ITAA 1997.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# Historical Base Rate Entity Tax Rates
BRE_RATES: dict[int, Decimal] = {
    2018: Decimal("0.275"),
    2019: Decimal("0.275"),
    2020: Decimal("0.275"),
    2021: Decimal("0.260"),
    2022: Decimal("0.250"),
    2023: Decimal("0.250"),
    2024: Decimal("0.250"),
    2025: Decimal("0.250"),
    2026: Decimal("0.250"),
    2027: Decimal("0.250"),
}

STANDARD_CORPORATE_RATE = Decimal("0.300")
TURNOVER_THRESHOLD = Decimal("50000000.00")  # $50M aggregated turnover threshold (s 328-115)
BREPI_THRESHOLD_PERCENT = Decimal("80.00")    # Passive income must not exceed 80% (s 23AB)


@dataclass(frozen=True)
class BaseRateEntityTest:
    financial_year: int
    aggregated_turnover: Decimal
    assessable_income: Decimal
    passive_income: Decimal  # Base Rate Entity Passive Income (BREPI)

    @property
    def passive_income_percentage(self) -> Decimal:
        if self.assessable_income <= Decimal("0.00"):
            return Decimal("100.00")
        pct = (self.passive_income / self.assessable_income) * Decimal("100.00")
        return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def is_aggregated_turnover_eligible(self) -> bool:
        return self.aggregated_turnover < TURNOVER_THRESHOLD

    @property
    def is_brepi_eligible(self) -> bool:
        return self.passive_income_percentage <= BREPI_THRESHOLD_PERCENT

    @property
    def is_base_rate_entity(self) -> bool:
        return self.is_aggregated_turnover_eligible and self.is_brepi_eligible


@dataclass(frozen=True)
class CorporateTaxRate:
    financial_year: int
    is_base_rate_entity: bool
    applicable_rate: Decimal
    rate_description: str
    statutory_basis: str


def bre_rate_for(fy: int) -> Decimal:
    try:
        return BRE_RATES[fy]
    except KeyError as exc:
        raise ValueError(
            f"No legislated BRE rate is tabulated for FY{fy}"
        ) from exc


def determine_corporate_tax_rate(test: BaseRateEntityTest) -> CorporateTaxRate:
    """
    Determine the company tax rate under s23AA Income Tax Rates Act 1986.
    """
    fy = test.financial_year
    is_bre = test.is_base_rate_entity
    if fy not in BRE_RATES:
        raise ValueError(f"No legislated company-rate table exists for FY{fy}")

    if is_bre:
        rate = bre_rate_for(fy)
        desc = f"Base Rate Entity ({rate * 100:.1f}%)"
        basis = "s 23AA Income Tax Rates Act 1986; turnover < $50M and BREPI <= 80%"
    else:
        rate = STANDARD_CORPORATE_RATE
        desc = "Standard Corporate Tax Rate (30.0%)"
        basis = "s 23(2) Income Tax Rates Act 1986; exceeds turnover or BREPI threshold"

    return CorporateTaxRate(
        financial_year=fy,
        is_base_rate_entity=is_bre,
        applicable_rate=rate,
        rate_description=desc,
        statutory_basis=basis,
    )


def determine_max_franking_rate(
    current_fy: int,
    prior_year_test: Optional[BaseRateEntityTest] = None,
) -> Decimal:
    """
    Determine corporate tax rate for imputation / maximum franking rate under
    s 202-60 / s 202-61 ITAA 1997.

    The maximum franking rate for a distribution in year N is the corporate tax rate
    determined based on the company's Base Rate Entity status in year N-1.
    If the company did not exist in year N-1, the tax rate for year N is used.
    """
    if prior_year_test is None:
        raise ValueError(
            f"prior_year_test is required for FY{current_fy}; "
            "the maximum franking rate is not assumed"
        )
    prior_res = determine_corporate_tax_rate(prior_year_test)
    return prior_res.applicable_rate
