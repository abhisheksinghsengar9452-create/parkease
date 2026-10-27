from services.recognition import DuplicateSuppressor, parse_ocr_candidate, select_plate_candidate


def test_low_confidence_requires_manual_review():
    result = parse_ocr_candidate('UP14 AB 1234', 72.0)
    assert result.normalized_plate == 'UP14AB1234'
    assert result.requires_review


def test_invalid_plate_requires_manual_review():
    assert parse_ocr_candidate('???', 99).requires_review


def test_duplicate_suppression():
    suppressor = DuplicateSuppressor(10)
    assert not suppressor.is_duplicate('UP14AB1234')
    assert suppressor.is_duplicate('UP14AB1234')


def test_combines_indian_plate_fragments_and_corrects_digit_lookalike():
    up14_box = [[0, 0], [40, 0], [40, 20], [0, 20]]
    suffix_box = [[42, 0], [125, 0], [125, 20], [42, 20]]
    result = select_plate_candidate([(up14_box, 'UPI4', 0.18), (suffix_box, 'AB 1234', 0.963)])
    assert result.raw_text == 'UPI4 AB 1234'
    assert result.normalized_plate == 'UP14AB1234'
    assert result.requires_review
