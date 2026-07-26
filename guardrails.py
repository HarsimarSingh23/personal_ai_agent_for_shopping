import re
import logging

log = logging.getLogger(__name__)

# Basic regex for catching 13 to 19 digit credit card numbers, with or without spaces/dashes.
CC_REGEX = re.compile(r'\b(?:\d[ -]*?){13,19}\b')

def mask_credit_card(text: str) -> str:
    """
    Scans the text for potential credit card numbers and masks them.
    Leaves the last 4 digits visible.
    Example: 4111-1111-1111-1111 -> ****-****-****-1111
    """
    if not text:
        return text

    def replacer(match):
        cc_str = match.group(0)
        digits_only = re.sub(r'[\s-]', '', cc_str)
        if len(digits_only) >= 13 and len(digits_only) <= 19 and digits_only.isdigit():
            log.warning("DLP Guardrail triggered: Masked a credit card number in the text.")
            masked = []
            digit_count = 0
            total_digits = len(digits_only)
            for char in cc_str:
                if char.isdigit():
                    digit_count += 1
                    if total_digits - digit_count < 4:
                        masked.append(char)
                    else:
                        masked.append('*')
                else:
                    masked.append(char)
            return "".join(masked)
        return cc_str

    return CC_REGEX.sub(replacer, text)
