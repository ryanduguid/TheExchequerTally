"""
EdwinNixon: Corporate Tax & Franking Account Imputation Engine
Named after Sir Edwin Van-der-Vord Nixon CMG (1876–1955), pioneer of Australian corporate accounting and taxation policy.
"""

__version__ = "0.1.0"
__author__ = "Ryan Duguid"

from .corporate_tax import (
    CorporateTaxRate,
    BaseRateEntityTest,
    determine_corporate_tax_rate,
    determine_max_franking_rate,
)
from .franking_account import (
    FrankingAccount,
    FrankingEntry,
    FrankingEntryType,
    FrankingDeficitResult,
)
from .benchmark_rule import (
    BenchmarkRuleValidator,
    DistributionEvent,
    BenchmarkRuleViolation,
)
from .distribution_statement import (
    DistributionStatement,
    generate_distribution_statement,
)

__all__ = [
    "CorporateTaxRate",
    "BaseRateEntityTest",
    "determine_corporate_tax_rate",
    "determine_max_franking_rate",
    "FrankingAccount",
    "FrankingEntry",
    "FrankingEntryType",
    "FrankingDeficitResult",
    "BenchmarkRuleValidator",
    "DistributionEvent",
    "BenchmarkRuleViolation",
    "DistributionStatement",
    "generate_distribution_statement",
]