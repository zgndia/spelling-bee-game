import edge_tts
import asyncio
import os
import tempfile
import sounddevice as sd
import soundfile as sf
import threading
import random
import time
import msvcrt
import sys

# ─── SETTINGS ─────────────────────────────────────────────────────────────────

# If True, only the word is spoken; if False, adds a prompt phrase.
QUICK_MODE = True

# Delay (seconds) between rounds in “normal” mode
NORMAL_MODE_DELAY = 1.5

# ─── TEXT‑TO‑SPEECH HANDLER ──────────────────────────────────────────────────

class TTS:
    VOICE = "en-US-AriaNeural"

    @staticmethod
    async def _speak_async(text: str):
        try:
            comm = edge_tts.Communicate(text=text, voice=TTS.VOICE)
            temp_file = os.path.join(tempfile.gettempdir(), "temp_tts.wav")
            await comm.save(temp_file)
            data, sr = sf.read(temp_file)
            sd.play(data, samplerate=sr, blocking=True)
        except Exception as e:
            # If TTS fails, just print the text
            print(f"[TTS ERROR: {e}] {text}")
        finally:
            try:
                os.remove(temp_file)
            except OSError:
                pass

    @staticmethod
    def speak(text: str):
        """Run the async TTS in its own event loop (so we can call from anywhere)."""
        asyncio.run(TTS._speak_async(text))

    @staticmethod
    def speak_in_thread(text: str):
        t = threading.Thread(target=TTS.speak, args=(text,), daemon=True)
        t.start()
        return t

# ─── WORD GAME ────────────────────────────────────────────────────────────────

class SpellingGame:
    def __init__(self):
        self.words: list[str] = []
        self.guessed: set[str] = set()
        self.current_word: str | None = None
        self.repeat_flag = False

    def load_words(self, filename: str) -> bool:
        """Load words from file, skipping blank lines and comments."""
        if not os.path.isfile(filename):
            print(f"❌ File not found: {filename}")
            input("> Press Enter to continue...")
            return False
        with open(filename, encoding="utf-8") as f:
            lines = [line.strip() for line in f]
        self.words = [
            w.replace("- ", "")
            for w in lines
            if w and not w.startswith("--")
        ]
        if not self.words:
            print("❌ No valid words in file.")
            input("> Press Enter to continue...")
            return False
        self.guessed.clear()
        return True

    def flush_input(self):
        """Clear any buffered keystrokes (Windows-only)."""
        while msvcrt.kbhit():
            msvcrt.getch()

    def pick_word(self):
        """Choose a new word the user hasn’t guessed yet."""
        remaining = [w for w in self.words if w not in self.guessed]
        self.current_word = random.choice(remaining)

    def smart_delay(self, length: int) -> float:
        """Dynamic delay based on word length."""
        return length / (4.5 + (length / 10))

    def play_round(self):
        os.system("cls")
        # Completed all?
        if len(self.guessed) == len(self.words):
            TTS.speak("Great job! You’ve spelled every word.")
            print("> You’ve guessed all the words! Returning to menu...")
            time.sleep(2)
            return False  # signal to exit loop

        # Decide the word to speak
        if self.repeat_flag and self.current_word:
            phrase = self.current_word
            self.repeat_flag = False
        else:
            self.pick_word()
            if QUICK_MODE:
                phrase = self.current_word
            else:
                starter = random.choice(
                    ["Can you spell", "The next word is", "Alright, spell", "Your word is", "Spell"]
                )
                phrase = f"{starter}, {self.current_word}"

        print(f"> Guessed: {len(self.guessed)}/{len(self.words)}")
        t = TTS.speak_in_thread(phrase)
        t.join()  # wait for speech to finish

        self.flush_input()
        start = time.time()
        answer = input("> ").strip()
        elapsed = time.time() - start

        # Repeat request
        if answer.lower() in ("repeat", "r"):
            self.repeat_flag = True
            return True

        # Check correctness
        if self.current_word and answer.lower() == self.current_word.lower():
            self.guessed.add(self.current_word)
            if not QUICK_MODE:
                print(f"> Correct! It was '{self.current_word}'.")
                wpm = (len(answer) / 5) / (elapsed / 60) if elapsed > 0 else 0
                print(f"> WPM: {wpm:.2f}")
                TTS.speak_in_thread("Correct!")
        else:
            print(f"> The word was '{self.current_word}'.")
            if not QUICK_MODE:
                TTS.speak_in_thread("Incorrect!")
            elif QUICK_MODE:
                time.sleep(self.smart_delay(len(self.current_word or "")))

        # Delay before next round
        if not QUICK_MODE:
            time.sleep(self.smart_delay(len(self.current_word or "")))

        return True  # continue game

    def run(self):
        while self.play_round():
            pass

# ─── MENUS ────────────────────────────────────────────────────────────────────

def settings_menu():
    global QUICK_MODE
    while True:
        os.system("cls")
        print("===== SETTINGS =====")
        print(f"1. Quick mode: {QUICK_MODE}")
        print("2. Back")
        choice = input("> ").strip()
        if choice == "1":
            QUICK_MODE = not QUICK_MODE
        elif choice == "2":
            break

def play_menu():
    game = SpellingGame()
    while True:
        os.system("cls")
        print("===== PLAY =====")
        print("1. Advanced")
        print("2. Expert")
        print("3. Back")
        choice = input("> ").strip()
        if choice in ("1", "2"):
            filename = "advanced.txt" if choice == "1" else "expert.txt"
            if game.load_words(filename):
                game.run()
        elif choice == "3":
            break
        else:
            print("> Invalid choice.")
            time.sleep(1)

def main():
    try:
        while True:
            os.system("cls")
            print("===== SPELLING BEE GAME =====")
            print("1. Play")
            print("2. Settings")
            print("3. Exit")
            choice = input("> ").strip()
            if choice == "1":
                play_menu()
            elif choice == "2":
                settings_menu()
            elif choice == "3":
                break
            else:
                print("> Invalid choice.")
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n> Exiting...")

if __name__ == "__main__":
    main()
