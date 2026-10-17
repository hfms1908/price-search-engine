"""Normalização conservadora de capacidades, sem alterar preços ou modelos."""
import re

CAPACITY_PATTERN = re.compile(r'(?<![\w])(?P<value>\d+(?:[.,]\d+)?)\s*/?\s*(?P<unit>GB|TB|MB)\b', re.IGNORECASE)


def normalize_capacities(text: str) -> str:
    """Padroniza '8 GB', '8/GB' e '8GB' como '8gb'."""
    return CAPACITY_PATTERN.sub(
        lambda m: f"{m.group('value')}{m.group('unit').lower()}", text
    )
