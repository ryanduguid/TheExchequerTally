# The Exchequer Tally

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![tests](https://github.com/ryanduguid/TheExchequerTally/actions/workflows/ci.yml/badge.svg)](https://github.com/ryanduguid/TheExchequerTally/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ITAA 1997](https://img.shields.io/badge/Legislation-ITAA%201997%20Part%203--6-002B49)](https://www.legislation.gov.au/C2004A05138/latest/text)

**Corporate tax rate verification, franking account ledger tracking, and Division 203 benchmark rule compliance for Australian private and public companies.**

The repository name is the public project identity; the `edwinnixon` distribution and command remain compatibility identifiers.

Named after **Sir Edwin Van-der-Vord Nixon CMG (1876 to 1955)**, prominent Australian chartered accountant, commissioner on the Commonwealth Royal Commission on Taxation (1932 to 1934), and pioneer of modern Australian corporate accounting and tax policy.

---

## Core Features

- **Base Rate Entity (BRE) Testing**: Deterministic assessment under *s 23AA & s 23AB Income Tax Rates Act 1986* (evaluating aggregated turnover thresholds and Base Rate Entity Passive Income ratios).
- **Franking Account Ledger (FAB)**: Complete balance management under *Part 3-6 ITAA 1997*, tracking PAYG instalments, company tax payments, dividends paid/received, and tax refunds.
- **Franking Deficit Tax (FDT) & Offset Penalty**: Evaluates FDT liability under *s 205-45* and calculates the 30% tax offset reduction penalty under *s 205-70(6)* where the deficit exceeds 10% of annual credits.
- **Division 203 Benchmark Rule Engine**: Detects over-franking tax (*s 203-50(1)*) and franking debit shortfalls (*s 203-50(2)*) across distributions in a franking period.
- **Dividend Distribution Statements**: Builds the statement fields required by *s 202-75 / s 202-80*. This is a review helper, not a lodgment and not a compliance certificate.

---

## Quickstart

### Installation
```bash
pip install .
```

### CLI Usage
```bash
# Evaluate Base Rate Entity (BRE) status for FY2025
edwinnixon bre-test --fy 2025 --turnover 4500000 --assessable 800000 --passive 120000

# Generate a dividend distribution statement
edwinnixon dist-statement --entity "Acme Pty Ltd" --acn "123456789" --recipient "Jane Doe" --amount 15000 --franking-pct 100 --tax-rate 0.25
```

---

## Statutory Ground Truth & Test Harness

All mathematical operations execute via `decimal.Decimal` fixed-point arithmetic to guarantee zero floating-point drift across corporate tax and franking schedules.

| Statutory Domain | Primary Authority | Verification Invariant |
| :--- | :--- | :--- |
| **Base Rate Entity Status** | *Income Tax Rates Act 1986* s 23AA | 25% tax rate strictly bounded by Aggregated Turnover < $50M and BREPI <= 80%. |
| **Franking Credits & Debits** | *ITAA 1997* s 205-15, s 205-30 | Exact day-order ledger reconciliation of corporate PAYG and tax payments. |
| **FDT Offset Reduction** | *ITAA 1997* s 205-45, s 205-70(6) | Exact 30% offset reduction penalty applied when deficit exceeds 10% threshold. |
| **Benchmark Rule** | *ITAA 1997* ss 203-25 to 203-55 | Deterministic debit shortfall and over-franking tax determination per distribution period. |
| **Distribution Statements** | *ITAA 1997* ss 202-75, 202-80 | Precise franking credit formula: `Distribution * (Rate / (1 - Rate)) * Franking%`. |

### Automated Test Suite
- Run the full suite: `pytest tests/`
- The suite covers BRE eligibility, FDT penalty triggers, benchmark-rule checks, and distribution-statement generation. Do not treat a static badge as live coverage.

---

## Licence
MIT License. Created by Ryan Duguid.