"""Input validation for Smart Medic."""

from datetime import datetime
import math
from numbers import Integral, Real


_CONSCIOUSNESS_VALUES = {"Normal", "Moderate", "Severe", "Unresponsive"}
_BLEEDING_VALUES = {"None", "Mild", "Moderate", "Severe"}


def _require_value(value: object, field_name: str) -> None:
	"""Reject missing values before any field-specific validation."""
	if value is None:
		raise ValueError(f"{field_name} is required")
	if isinstance(value, str) and not value.strip():
		raise ValueError(f"{field_name} is required")
	if isinstance(value, Real) and math.isnan(value):
		raise ValueError(f"{field_name} is required")


def _validate_integer_range(
	value: object, field_name: str, minimum: int, maximum: int
) -> int:
	_require_value(value, field_name)
	if not isinstance(value, Integral) or isinstance(value, bool):
		raise ValueError(f"{field_name} must be an integer")
	if not minimum <= value <= maximum:
		raise ValueError(
			f"{field_name} must be between {minimum} and {maximum}"
		)
	return int(value)


def validate_age(age: object) -> int:
	"""Validate that age is an integer from 18 through 95."""
	return _validate_integer_range(age, "age", 18, 95)


def validate_spo2(spo2: object) -> int:
	"""Validate oxygen saturation as an integer percentage."""
	return _validate_integer_range(spo2, "spo2", 0, 100)


def validate_heart_rate(heart_rate: object) -> int:
	"""Validate heart rate in a broad physiologically plausible range."""
	return _validate_integer_range(heart_rate, "heart_rate", 20, 250)


def validate_respiratory_rate(respiratory_rate: object) -> int:
	"""Validate respiratory rate in a broad physiologically plausible range."""
	return _validate_integer_range(respiratory_rate, "respiratory_rate", 4, 60)


def validate_systolic_bp(systolic_bp: object) -> int:
	"""Validate systolic blood pressure in a broad plausible range."""
	return _validate_integer_range(systolic_bp, "systolic_bp", 50, 250)


def validate_pain_level(pain_level: object) -> int:
	"""Validate pain level as an integer from zero through ten."""
	return _validate_integer_range(pain_level, "pain_level", 0, 10)


def validate_consciousness(consciousness: object) -> str:
	"""Validate the allowed consciousness descriptor."""
	_require_value(consciousness, "consciousness")
	if not isinstance(consciousness, str) or consciousness not in _CONSCIOUSNESS_VALUES:
		allowed = ", ".join(sorted(_CONSCIOUSNESS_VALUES))
		raise ValueError(f"consciousness must be one of: {allowed}")
	return consciousness


def normalize_bleeding(bleeding: object) -> str:
	"""Convert blank or CSV NaN bleeding values to the explicit no-bleeding label."""
	if bleeding is None:
		return "None"
	if isinstance(bleeding, str):
		stripped = bleeding.strip()
		if not stripped or stripped.lower() == "nan":
			return "None"
		return stripped
	if isinstance(bleeding, Real) and math.isnan(bleeding):
		return "None"
	return str(bleeding)


def validate_bleeding(bleeding: object) -> str:
	"""Normalize and validate the allowed bleeding descriptor."""
	normalized = normalize_bleeding(bleeding)
	if normalized not in _BLEEDING_VALUES:
		allowed = ", ".join(sorted(_BLEEDING_VALUES))
		raise ValueError(f"bleeding must be one of: {allowed}")
	return normalized


def validate_arrival_time(arrival_time: object) -> datetime:
	"""Validate that arrival time is a datetime instance."""
	_require_value(arrival_time, "arrival_time")
	if not isinstance(arrival_time, datetime):
		raise ValueError("arrival_time must be a datetime")
	return arrival_time


def _validate_non_blank_text(value: object, field_name: str) -> str:
	_require_value(value, field_name)
	if not isinstance(value, str):
		raise ValueError(f"{field_name} must be a string")
	return value.strip()


def validate_name(name: object) -> str:
	"""Validate a non-blank patient name."""
	return _validate_non_blank_text(name, "name")


def validate_patient_id(patient_id: object) -> str:
	"""Validate a non-blank patient identifier."""
	return _validate_non_blank_text(patient_id, "patient_id")