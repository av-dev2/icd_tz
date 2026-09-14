"""UN/EDIFACT syntax helpers: level A character handling and segment assembly."""

from datetime import datetime

from frappe.utils import get_datetime

# UN/EDIFACT level A repertoire. Lowercase and anything outside this set is not transmittable.
UNOA_CHARACTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-()/'+:=?!\"%&*;<>")

# Segment terminator, element separator, component separator and the release character itself.
SERVICE_CHARACTERS = frozenset("+:'?")

RELEASE_CHARACTER = "?"
ELEMENT_SEPARATOR = "+"
COMPONENT_SEPARATOR = ":"
SEGMENT_TERMINATOR = "'"

DATE_FORMATS = {
	"102": "%Y%m%d",
	"203": "%Y%m%d%H%M",
	"204": "%Y%m%d%H%M%S",
}


def text(value, limit: int | None = None) -> str:
	"""A data value made safe to place inside a segment.

	Uppercased, stripped of characters outside level A, then the service
	characters are released so they cannot be read as structure.
	"""

	if value is None:
		return ""

	cleaned = "".join(character for character in str(value).strip().upper() if character in UNOA_CHARACTERS)
	if limit:
		cleaned = cleaned[:limit]

	return "".join(
		RELEASE_CHARACTER + character if character in SERVICE_CHARACTERS else character
		for character in cleaned
	)


def segment(tag: str, *elements) -> str:
	"""One segment, with its empty trailing elements dropped.

	An element is a string, or a list whose parts become components.
	"""

	values = [compose(element) for element in elements]

	return ELEMENT_SEPARATOR.join([tag, *trim(values)]) + SEGMENT_TERMINATOR


def compose(element) -> str:
	if isinstance(element, list | tuple):
		return COMPONENT_SEPARATOR.join(trim([str(part) if part is not None else "" for part in element]))

	return str(element) if element is not None else ""


def trim(values: list[str]) -> list[str]:
	"""Drop the empty values at the tail, the ones in the middle are positional"""

	trimmed = list(values)
	while trimmed and not trimmed[-1]:
		trimmed.pop()

	return trimmed


def edifact_datetime(value, format_code: str = "203") -> str:
	"""A date or datetime in the requested EDIFACT format, empty when there is no value"""

	if not value:
		return ""

	moment = value if isinstance(value, datetime) else get_datetime(value)

	return moment.strftime(DATE_FORMATS[format_code])


def whole_number(value) -> str:
	"""A measurement without a decimal part, which is what the carriers ask for"""

	if value in (None, ""):
		return ""

	return str(round(float(value)))
