import pytest

from app.tools.calculator import CalculatorError, evaluate_expression


def test_calculator_basic():
    assert evaluate_expression("2 + 2") == 4.0
    assert evaluate_expression("(10 - 3) * 2") == 14.0


def test_calculator_functions():
    assert evaluate_expression("sqrt(9)") == 3.0
    assert evaluate_expression("abs(-5)") == 5.0


def test_calculator_rejects_unsafe():
    with pytest.raises(CalculatorError):
        evaluate_expression("__import__('os').system('ls')")
    with pytest.raises(CalculatorError):
        evaluate_expression("open('/etc/passwd')")
