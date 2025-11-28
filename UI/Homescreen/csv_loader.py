"""Reads the splash.csv file and returns the list of splash screen texts."""

def load_splash_texts() -> list[str]:
    """Loads splash screen texts from a CSV file.

    Returns:
        A list of splash screen texts.
    """
    file = "UI/Homescreen/splash.csv"

    texts = []
    try:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    texts.append(line)

    except FileNotFoundError:
        print(f"Warning: {file} not found. No splash texts loaded.")

    # Split into two different lists, one for text without * and one for text with *
    no_asterisk_texts = [text for text in texts if "*" not in text]
    asterisk_texts = [text for text in texts if "*" in text]

    return texts, no_asterisk_texts, asterisk_texts