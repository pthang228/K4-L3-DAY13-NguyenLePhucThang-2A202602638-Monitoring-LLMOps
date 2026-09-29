from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd_credit_card_and_passport() -> None:
    samples = (
        ("CCCD 001234567890", "001234567890", "REDACTED_CCCD"),
        ("Card 4111 1111 1111 1111", "4111 1111 1111 1111", "REDACTED_CREDIT_CARD"),
        ("Passport B1234567", "B1234567", "REDACTED_PASSPORT"),
    )

    for text, raw_value, marker in samples:
        out = scrub_text(text)
        assert raw_value not in out
        assert marker in out
