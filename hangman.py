#!/usr/bin/env python3
"""
Grateful Dead Hangman
A single-player hangman game where every answer is a Grateful Dead song.
"""

import random
import os

SONGS = [
    "Truckin",
    "Ripple",
    "Casey Jones",
    "Friend of the Devil",
    "Sugar Magnolia",
    "Scarlet Begonias",
    "Touch of Grey",
    "Uncle Johns Band",
    "Fire on the Mountain",
    "Eyes of the World",
    "Terrapin Station",
    "Dark Star",
    "China Cat Sunflower",
    "Box of Rain",
    "Brokedown Palace",
    "Althea",
    "Bertha",
    "Estimated Prophet",
    "St Stephen",
    "Shakedown Street",
    "Tennessee Jed",
    "Morning Dew",
    "Playing in the Band",
    "The Other One",
    "Wharf Rat",
    "Not Fade Away",
    "Jack Straw",
    "Deal",
    "Sugaree",
    "Brown Eyed Women",
    "Ramble on Rose",
    "He's Gone",
    "Stella Blue",
    "Mississippi Half Step",
    "New Speedway Boogie",
    "Cumberland Blues",
    "Dire Wolf",
    "High Time",
    "Operator",
    "Candyman",
    "Loser",
    "Bird Song",
    "Greatest Story Ever Told",
    "Mexicali Blues",
    "They Love Each Other",
    "Ship of Fools",
    "Franklin's Tower",
    "Help on the Way",
    "Slipknot",
    "The Music Never Stopped",
    "Crazy Fingers",
    "Blues for Allah",
    "Samson and Delilah",
    "Sunrise",
    "Passenger",
    "Lazy Lightning",
    "Supplication",
    "Peggy O",
    "Cold Rain and Snow",
    "Alabama Getaway",
    "Feel Like a Stranger",
    "Lost Sailor",
    "Saint of Circumstance",
    "Far From Me",
    "Throwing Stones",
    "Hell in a Bucket",
    "West LA Fadeaway",
    "Black Muddy River",
    "Standing on the Moon",
    "Foolish Heart",
    "Built to Last",
    "Picasso Moon",
    "Liberty",
    "So Many Roads",
    "Days Between",
    "Cosmic Charlie",
    "Cryptical Envelopment",
    "Rosemary",
    "Mountains of the Moon",
    "Duprees Diamond Blues",
    "Cream Puff War",
    "Golden Road",
    "Here Comes Sunshine",
    "Row Jimmy",
    "Loose Lucy",
    "Unbroken Chain",
    "Scarlet Fire",
    "Comes a Time",
    "Might as Well",
    "Mission in the Rain",
    "Weather Report Suite",
    "Let it Grow",
    "Wave to the Wind",
    "Pride of Cucamonga",
    "Money Money",
    "Born Cross Eyed",
    "Black Peter",
    "Easy Wind",
    "Attics of My Life",
    "Til the Morning Comes",
    "To Lay Me Down",
]

HANGMAN_STAGES = [
    """
      ------
      |    |
      |
      |
      |
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |
      |
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |    |
      |
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |   /|
      |
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |   /|\\
      |
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |   /|\\
      |   /
      |
    ------
    """,
    """
      ------
      |    |
      |    O
      |   /|\\
      |   / \\
      |
    ------
    """,
]

MAX_WRONG = len(HANGMAN_STAGES) - 1


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def display_board(wrong_guesses, guessed_letters, display_word):
    clear_screen()
    print("=" * 44)
    print("       GRATEFUL DEAD HANGMAN")
    print("=" * 44)
    print(HANGMAN_STAGES[wrong_guesses])
    print(f"  Song:  {display_word}")
    print(f"  Wrong: {', '.join(sorted(guessed_letters)) if guessed_letters else '(none)'}")
    print(f"  Guesses left: {MAX_WRONG - wrong_guesses}")
    print("-" * 44)


def build_display(song, correct_guesses):
    """Build the display string, revealing correctly guessed letters."""
    display = []
    for ch in song:
        if ch == " ":
            display.append("  ")
        elif ch.upper() in correct_guesses:
            display.append(ch)
        elif not ch.isalpha():
            display.append(ch)
        else:
            display.append("_")
    return " ".join(display)


def is_solved(song, correct_guesses):
    return all(
        ch.upper() in correct_guesses or not ch.isalpha() for ch in song
    )


def play_round():
    song = random.choice(SONGS)
    correct_guesses = set()
    wrong_letters = set()
    wrong_count = 0

    while True:
        display_word = build_display(song, correct_guesses)
        display_board(wrong_count, wrong_letters, display_word)

        if is_solved(song, correct_guesses):
            print(f'\n  You got it! The song is "{song}".')
            print("  What a long, strange trip it\'s been!\n")
            return True

        if wrong_count >= MAX_WRONG:
            print(f'\n  Game over! The song was "{song}".')
            print("  Looks like you need more time on the bus.\n")
            return False

        guess = input("\n  Guess a letter: ").strip().upper()

        if len(guess) != 1 or not guess.isalpha():
            input("  Please enter a single letter. (press Enter)")
            continue

        if guess in correct_guesses or guess in wrong_letters:
            input("  You already guessed that letter. (press Enter)")
            continue

        if guess in song.upper():
            correct_guesses.add(guess)
        else:
            wrong_letters.add(guess)
            wrong_count += 1


def main():
    clear_screen()
    print("=" * 44)
    print("       GRATEFUL DEAD HANGMAN")
    print("=" * 44)
    print()
    print("  Guess the Grateful Dead song title,")
    print("  one letter at a time!")
    print()
    print("  You get 6 wrong guesses before")
    print("  the Deadhead is hung.")
    print()
    input("  Press Enter to start...")

    wins = 0
    games = 0

    while True:
        games += 1
        if play_round():
            wins += 1

        print(f"  Score: {wins} wins out of {games} games")
        again = input("\n  Play again? (y/n): ").strip().lower()
        if again != "y":
            break

    print()
    print(f"  Final score: {wins}/{games}")
    print("  Fare thee well, Deadhead!")
    print()


if __name__ == "__main__":
    main()
