from datetime import date
from decimal import Decimal
from edwinnixon.corporate_tax import BaseRateEntityTest, determine_corporate_tax_rate, determine_max_franking_rate
from edwinnixon.franking_account import FrankingAccount, FrankingEntryType
from edwinnixon.benchmark_rule import BenchmarkRuleValidator, DistributionEvent
from edwinnixon.distribution_statement import generate_distribution_statement

def test_base_rate_entity_eligibility():
    # Eligible BRE (< $50M and passive <= 80%)
    bre_test = BaseRateEntityTest(
        financial_year=2025,
        aggregated_turnover=Decimal("15000000.00"),
        assessable_income=Decimal("1200000.00"),
        passive_income=Decimal("300000.00"),  # 25% passive
    )
    res = determine_corporate_tax_rate(bre_test)
    assert res.is_base_rate_entity is True
    assert res.applicable_rate == Decimal("0.25")

    # Ineligible due to high passive income (> 80%)
    high_passive = BaseRateEntityTest(
        financial_year=2025,
        aggregated_turnover=Decimal("2000000.00"),
        assessable_income=Decimal("100000.00"),
        passive_income=Decimal("85000.00"),  # 85% passive
    )
    res_passive = determine_corporate_tax_rate(high_passive)
    assert res_passive.is_base_rate_entity is False
    assert res_passive.applicable_rate == Decimal("0.30")

    # Ineligible due to turnover >= $50M
    large_co = BaseRateEntityTest(
        financial_year=2025,
        aggregated_turnover=Decimal("60000000.00"),
        assessable_income=Decimal("10000000.00"),
        passive_income=Decimal("500000.00"),
    )
    res_large = determine_corporate_tax_rate(large_co)
    assert res_large.is_base_rate_entity is False
    assert res_large.applicable_rate == Decimal("0.30")

def test_franking_account_ledger_and_fdt():
    account = FrankingAccount(financial_year=2025, opening_balance=Decimal("1000.00"))
    
    # Add PAYG instalment
    account.record_payg_instalment(date(2024, 10, 28), Decimal("5000.00"))
    # Add franked dividend received
    account.record_franked_distribution_received(date(2024, 12, 1), Decimal("1200.00"))
    # Pay franked dividend
    account.record_franked_distribution_paid(date(2025, 3, 15), Decimal("4000.00"))

    assert account.total_credits == Decimal("6200.00")
    assert account.total_debits == Decimal("4000.00")
    assert account.closing_balance == Decimal("3200.00")

    fdt_eval = account.evaluate_franking_deficit()
    assert fdt_eval.has_deficit is False
    assert fdt_eval.franking_deficit_tax == Decimal("0.00")

def test_franking_deficit_tax_and_penalty():
    account = FrankingAccount(financial_year=2025, opening_balance=Decimal("0.00"))
    account.record_payg_instalment(date(2024, 10, 28), Decimal("1000.00"))
    # Pay distribution far exceeding credits
    account.record_franked_distribution_paid(date(2025, 6, 30), Decimal("3000.00"))

    assert account.closing_balance == Decimal("-2000.00")
    fdt_eval = account.evaluate_franking_deficit()
    assert fdt_eval.has_deficit is True
    assert fdt_eval.franking_deficit_tax == Decimal("2000.00")
    # Deficit $2000 > 10% of $1000 ($100), so 30% reduction applies under s 205-70(6)
    assert fdt_eval.fdt_offset_reduction_applies is True
    assert fdt_eval.allowable_tax_offset == Decimal("1400.00")  # 70% of $2000

def test_benchmark_rule_validation():
    validator = BenchmarkRuleValidator(corporate_tax_rate=Decimal("0.25"))

    # First distribution: fully franked ($75,000 cash, $25,000 credit -> 100% franked)
    dist1 = DistributionEvent(
        event_date=date(2024, 9, 30),
        recipient_name="Shareholder A",
        distribution_amount=Decimal("75000.00"),
        franking_credit=Decimal("25000.00"),
        corporate_tax_rate=Decimal("0.25"),
    )
    validator.add_distribution(dist1)
    assert validator.benchmark_percentage == Decimal("100.00")

    # Second distribution: under-franked ($75,000 cash, $12,500 credit -> 50% franked)
    dist2 = DistributionEvent(
        event_date=date(2025, 3, 31),
        recipient_name="Shareholder B",
        distribution_amount=Decimal("75000.00"),
        franking_credit=Decimal("12500.00"),
        corporate_tax_rate=Decimal("0.25"),
    )
    validator.add_distribution(dist2)

    is_compliant, violations = validator.validate_distributions()
    assert is_compliant is False
    assert len(violations) == 1
    assert violations[0].consequence_type == "FRANKING_DEBIT"
    assert violations[0].penalty_or_debit_amount == Decimal("12500.00")

def test_distribution_statement_generation():
    stmt = generate_distribution_statement(
        entity_name="Acme Holdings Pty Ltd",
        abn_or_acn="12 345 678 901",
        recipient_name="Jane Doe",
        payment_date=date(2025, 4, 1),
        total_distribution=Decimal("10000.00"),
        franking_percentage=Decimal("100.00"),
        corporate_tax_rate=Decimal("0.25"),
    )
    assert stmt.franked_amount == Decimal("10000.00")
    assert stmt.unfranked_amount == Decimal("0.00")
    # 10000 * (0.25 / 0.75) = 3333.33
    assert stmt.franking_credit == Decimal("3333.33")
    assert stmt.gross_assessable_income == Decimal("13333.33")