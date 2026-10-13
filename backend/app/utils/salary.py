"""Salary normalization. Amounts are compared only after converting to EUR per year, so a monthly
salary is never compared directly with an annual one."""

from app.models.enums import SalaryPeriod

# Belgian convention: 13.92 monthly salaries per year (12 + end-of-year bonus + double holiday pay).
MONTHS_PER_YEAR = 13.92
HOURS_PER_YEAR = 38 * 52

# Only EUR is converted for now. Other currencies are stored but excluded from cross-currency comparisons.
_TO_EUR = {"EUR": 1.0}


def to_annual_eur(amount: int | None, period: SalaryPeriod | str | None, currency: str = "EUR") -> int | None:
    if amount is None or period is None:
        return None
    rate = _TO_EUR.get(currency.upper())
    if rate is None:
        return None
    period = SalaryPeriod(period)
    factor = {SalaryPeriod.YEAR: 1.0, SalaryPeriod.MONTH: MONTHS_PER_YEAR, SalaryPeriod.HOUR: HOURS_PER_YEAR}[period]
    return round(amount * factor * rate)
