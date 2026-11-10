"""Normalização conservadora de capacidades, sem alterar preços ou modelos."""
import re

CAPACITY_PATTERN = re.compile(
    r'(?<!\d)(?P<value>\d+(?:[.,]\d+)?)'
    r'\s*/?\s*(?P<unit>GB|TB|MB)',
    re.IGNORECASE
)


def normalize_capacity_value(value: str) -> str:
    """Normaliza separadores numéricos de capacidades."""

    if re.fullmatch(r'[1-9]\.\d{3}', value):
        return value.replace('.', '')

    return value.replace(',', '.')


def normalize_capacities(text: str) -> str:
    """Padroniza capacidades e separa palavras concatenadas."""

    def replace_capacity(match):
        value = normalize_capacity_value(match.group('value'))
        unit = match.group('unit').lower()

        return f' {value}{unit} '

    return re.sub(
        r'\s+',
        ' ',
        CAPACITY_PATTERN.sub(replace_capacity, text)
    ).strip()
