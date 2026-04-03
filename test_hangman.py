"""Tests for the Grateful Dead hangman game."""

from hangman import SONGS, HANGMAN_STAGES, MAX_WRONG, build_display, is_solved


def test_songs_not_empty():
    assert len(SONGS) > 0


def test_no_duplicate_songs():
    assert len(SONGS) == len(set(SONGS))


def test_hangman_stages_count():
    assert len(HANGMAN_STAGES) == 7
    assert MAX_WRONG == 6


def test_build_display_hides_unguessed():
    display = build_display("Ripple", set())
    assert "R" not in display
    assert "_" in display


def test_build_display_reveals_guessed():
    display = build_display("Ripple", {"R", "P"})
    assert "R" in display
    assert "p" in display


def test_build_display_spaces_shown():
    display = build_display("Dark Star", set())
    # Spaces between words use double-space separator
    assert "  " in display


def test_build_display_punctuation_shown():
    display = build_display("He's Gone", set())
    assert "'" in display


def test_is_solved_false_when_incomplete():
    assert not is_solved("Ripple", {"R", "P"})


def test_is_solved_true_when_complete():
    assert is_solved("Ripple", {"R", "I", "P", "L", "E"})


def test_is_solved_ignores_spaces_and_punctuation():
    assert is_solved("He's Gone", {"H", "E", "S", "G", "O", "N"})
