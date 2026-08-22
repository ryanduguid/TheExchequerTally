import pytest
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


def test_unknown_financial_year_is_refused():
    unknown = BaseRateEntityTest(
        financial_year=2010,
        aggregated_turnover=Decimal("1000000.00"),
        assessable_income=Decimal("100000.00"),
        passive_income=Decimal("10000.00"),
    )
    try:
        determine_corporate_tax_rate(unknown)
    except ValueError as exc:
        assert "FY2010" in str(exc)
    else:
        raise AssertionError("unknown years must not receive a guessed rate")


def test_max_franking_rate_requires_prior_year():
    try:
        determine_max_franking_rate(2025)
    except ValueError as exc:
        assert "prior_year_test" in str(exc)
    else:
        raise AssertionError("franking rate must not assume BRE")


def test_max_franking_rate_uses_current_year_rate_scale():
    # s 995-1: prior-year AMOUNTS, current-year rate scale. Across the
    # 2020-21 and 2021-22 transitions the old prior-year-scale lookup
    # over-stated the rate (0.275/0.260 instead of 0.260/0.250).
    prior_2020 = BaseRateEntityTest(
        financial_year=2020,
        aggregated_turnover=Decimal("10000000.00"),
        assessable_income=Decimal("1000000.00"),
        passive_income=Decimal("100000.00"),
    )
    assert determine_max_franking_rate(2021, prior_2020) == Decimal("0.260")
    prior_2021 = BaseRateEntityTest(
        financial_year=2021,
        aggregated_turnover=Decimal("10000000.00"),
        assessable_income=Decimal("1000000.00"),
        passive_income=Decimal("100000.00"),
    )
    assert determine_max_franking_rate(2022, prior_2021) == Decimal("0.250")


def test_fy2018_turnover_threshold_is_25m():
    # Enterprise Tax Plan Act 2017 Sch 1 Pt 2: $25M for 2017-18;
    # Pt 3 item 16 substitutes $50M from 2018-19.
    forty_m_2018 = BaseRateEntityTest(
        financial_year=2018,
        aggregated_turnover=Decimal("40000000.00"),
        assessable_income=Decimal("10000000.00"),
        passive_income=Decimal("1000000.00"),
    )
    res = determine_corporate_tax_rate(forty_m_2018)
    assert not res.is_base_rate_entity
    assert res.applicable_rate == Decimal("0.300")
    just_under_2018 = BaseRateEntityTest(
        financial_year=2018,
        aggregated_turnover=Decimal("24999999.99"),
        assessable_income=Decimal("10000000.00"),
        passive_income=Decimal("1000000.00"),
    )
    assert determine_corporate_tax_rate(just_under_2018).is_base_rate_entity


def test_brepi_test_compares_exactly_not_rounded():
    # 80.004% rounds to 80.00 but is over the statutory limit.
    over = BaseRateEntityTest(
        financial_year=2025,
        aggregated_turnover=Decimal("10000000.00"),
        assessable_income=Decimal("1000000.00"),
        passive_income=Decimal("800040.00"),
    )
    assert not over.is_brepi_eligible
    at_limit = BaseRateEntityTest(
        financial_year=2025,
        aggregated_turnover=Decimal("10000000.00"),
        assessable_income=Decimal("1000000.00"),
        passive_income=Decimal("800000.00"),
    )
    assert at_limit.is_brepi_eligible


def test_fdt_reduction_applies_with_zero_credits():
    # 10% of zero credits is zero; any deficit exceeds it (s 205-70).
    account = FrankingAccount(financial_year=2025, opening_balance=Decimal("0.00"))
    account.record_franked_distribution_paid(date(2025, 3, 1), Decimal("3000.00"))
    result = account.evaluate_franking_deficit()
    assert result.fdt_offset_reduction_applies
    assert result.allowable_tax_offset == Decimal("2100.00")


def test_under_franking_debit_and_fdt_liability_entries():
    account = FrankingAccount(financial_year=2025, opening_balance=Decimal("100.00"))
    debit = account.record_under_franking_debit(date(2025, 4, 1), Decimal("40.00"))
    assert debit.is_debit
    credit = account.record_fdt_liability(date(2025, 6, 30), Decimal("10.00"))
    assert credit.is_credit
    assert account.closing_balance == Decimal("70.00")


def test_negative_amounts_are_refused():
    with pytest.raises(ValueError):
        BaseRateEntityTest(
            financial_year=2025,
            aggregated_turnover=Decimal("-5000000.00"),
            assessable_income=Decimal("1000000.00"),
            passive_income=Decimal("100000.00"),
        )
    account = FrankingAccount(financial_year=2025)
    with pytest.raises(ValueError):
        account.record_payg_instalment(date(2025, 1, 1), Decimal("-10.00"))
    with pytest.raises(ValueError):
        generate_distribution_statement(
            entity_name="X Pty Ltd",
            abn_or_acn="12 345 678 901",
            recipient_name="Y",
            payment_date=date(2025, 1, 1),
            total_distribution=Decimal("-10000.00"),
            franking_percentage=Decimal("100.00"),
        )
    with pytest.raises(ValueError):
        generate_distribution_statement(
            entity_name="X Pty Ltd",
            abn_or_acn="12 345 678 901",
            recipient_name="Y",
            payment_date=date(2025, 1, 1),
            total_distribution=Decimal("10000.00"),
            franking_percentage=Decimal("150.00"),
        )


def test_franking_credit_never_exceeds_statutory_maximum():
    # $100.01 fully franked at 25%: maximum credit is 100.01/3 = 33.3366...;
    # HALF_UP printed 33.34, above the s 202-60 cap. ROUND_DOWN gives 33.33.
    stmt = generate_distribution_statement(
        entity_name="X Pty Ltd",
        abn_or_acn="12 345 678 901",
        recipient_name="Y",
        payment_date=date(2025, 1, 1),
        total_distribution=Decimal("100.01"),
        franking_percentage=Decimal("100.00"),
        corporate_tax_rate=Decimal("0.25"),
    )
    assert stmt.franking_credit == Decimal("33.33")


def test_benchmark_percentage_caps_at_100():
    validator = BenchmarkRuleValidator(corporate_tax_rate=Decimal("0.25"))
    over_credited = DistributionEvent(
        event_date=date(2025, 1, 15),
        recipient_name="A",
        distribution_amount=Decimal("75000.00"),
        franking_credit=Decimal("30000.00"),  # above the $25,000 maximum
    )
    validator.add_distribution(over_credited)
    assert validator.benchmark_percentage == Decimal("100.00")
    fully_franked = DistributionEvent(
        event_date=date(2025, 2, 15),
        recipient_name="B",
        distribution_amount=Decimal("75000.00"),
        franking_credit=Decimal("25000.00"),
    )
    validator.add_distribution(fully_franked)
    ok, violations = validator.validate_distributions()
    assert ok, violations


def test_benchmark_comparison_works_in_dollars():
    # A $10,000.01 credit against a $10,000.00 benchmark on a $30,000
    # distribution is a real variance a rounded-percentage comparison missed.
    validator = BenchmarkRuleValidator(corporate_tax_rate=Decimal("0.25"))
    validator.add_distribution(DistributionEvent(
        event_date=date(2025, 1, 15),
        recipient_name="A",
        distribution_amount=Decimal("30000.00"),
        franking_credit=Decimal("10000.00"),
    ))
    validator.add_distribution(DistributionEvent(
        event_date=date(2025, 2, 15),
        recipient_name="B",
        distribution_amount=Decimal("30000.00"),
        franking_credit=Decimal("10000.02"),
    ))
    ok, violations = validator.validate_distributions()
    assert not ok
    assert violations[0].consequence_type == "OVER_FRANKING_TAX"
