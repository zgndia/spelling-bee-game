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
import json

# ─── SETTINGS ─────────────────────────────────────────────────────────────────

QUICK_MODE = True
WORDS_FOLDER = "words"
WORDS_JSON = "words.json"

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
            print(f"[TTS ERROR: {e}] {text}")
        finally:
            try:
                os.remove(temp_file)
            except OSError:
                pass

    @staticmethod
    def speak(text: str):
        asyncio.run(TTS._speak_async(text))

    @staticmethod
    def speak_in_thread(text: str):
        t = threading.Thread(target=TTS.speak, args=(text,), daemon=True)
        t.start()
        return t

# ─── WORD HANDLER ─────────────────────────────────────────────────────────────

def get_difficulty_files() -> dict:
    files = {}
    if not os.path.isdir(WORDS_FOLDER):
        os.makedirs(WORDS_FOLDER)
    for filename in os.listdir(WORDS_FOLDER):
        if filename.endswith(".txt"):
            name = os.path.splitext(filename)[0].capitalize()
            files[name] = filename
    return files

def generate_words_json():
    words_data = {}
    difficulty_files = get_difficulty_files()
    for difficulty, filename in difficulty_files.items():
        full_path = os.path.join(WORDS_FOLDER, filename)
        if os.path.isfile(full_path):
            entries = []
            with open(full_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("--"):
                        aliases = [w.strip() for w in line.split(",") if w.strip()]
                        if aliases:
                            entries.append(aliases)
            words_data[difficulty] = entries
        else:
            print(f"⚠️ Missing file: {full_path}")
            words_data[difficulty] = []
    with open(WORDS_JSON, "w", encoding="utf-8") as f:
        json.dump(words_data, f, ensure_ascii=False, indent=2)
    print("✅ words.json created successfully.")

def load_words_from_json(difficulty: str) -> list[list[str]]:
    with open(WORDS_JSON, encoding="utf-8") as f:
        all_words = json.load(f)
    return all_words.get(difficulty, [])

# ─── WORD GAME ────────────────────────────────────────────────────────────────

class SpellingGame:
    def __init__(self):
        self.words: list[list[str]] = []
        self.guessed: set[str] = set()
        self.current_word: list[str] | None = None
        self.repeat_flag = False

    def load_words(self, difficulty: str) -> bool:
        self.words = load_words_from_json(difficulty)
        if not self.words:
            print(f"❌ No words found for '{difficulty}'")
            input("> Press Enter to continue...")
            return False
        self.guessed.clear()
        return True

    def flush_input(self):
        while msvcrt.kbhit():
            msvcrt.getch()

    def pick_word(self):
        remaining = [w for w in self.words if tuple(w) not in self.guessed]
        self.current_word = random.choice(remaining)

    def smart_delay(self, length: int) -> float:
        return length / (4.5 + (length / 10))

    def play_round(self):
        os.system("cls")
        if len(self.guessed) == len(self.words):
            print("> You’ve guessed all the words! Returning to menu...")
            TTS.speak("Great job! You’ve spelled every word.")
            time.sleep(2)
            return False

        if self.repeat_flag and self.current_word:
            phrase = self.current_word[0]
            self.repeat_flag = False
        else:
            self.pick_word()
            phrase = self.current_word[0] if QUICK_MODE else f"{random.choice(['Can you spell', 'Spell', 'Your word is'])}, {self.current_word[0]}"

        print(f"> Guessed: {len(self.guessed)}/{len(self.words)}")
        t = TTS.speak_in_thread(phrase)
        t.join()

        self.flush_input()
        start = time.time()
        answer = input("> ").strip()
        elapsed = time.time() - start

        if answer.lower() in ("repeat", "r"):
            self.repeat_flag = True
            return True

        if self.current_word and answer.lower() in [w.lower() for w in self.current_word]:
            self.guessed.add(tuple(self.current_word))
            if not QUICK_MODE:
                print(f"> Correct! It was '{self.current_word[0]}'.")
                wpm = (len(answer) / 5) / (elapsed / 60) if elapsed > 0 else 0
                print(f"> WPM: {wpm:.2f}")
                TTS.speak_in_thread("Correct!")
        else:
            print(f"> The word was '{self.current_word[0]}'.")
            if not QUICK_MODE:
                TTS.speak_in_thread("Incorrect!")
            elif QUICK_MODE:
                time.sleep(self.smart_delay(len(self.current_word[0])))

        if not QUICK_MODE:
            time.sleep(self.smart_delay(len(self.current_word[0])))

        return True

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
    with open(WORDS_JSON, encoding="utf-8") as f:
        difficulties = list(json.load(f).keys())
    while True:
        os.system("cls")
        print("===== PLAY =====")
        for i, diff in enumerate(difficulties, start=1):
            print(f"{i}. {diff}")
        print(f"{len(difficulties)+1}. Back")
        choice = input("> ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(difficulties):
                difficulty = difficulties[idx - 1]
                if game.load_words(difficulty):
                    game.run()
            elif idx == len(difficulties) + 1:
                break
            else:
                print("> Invalid choice.")
                time.sleep(1)
        else:
            print("> Invalid input.")
            time.sleep(1)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    try:
        generate_words_json()  # Always refresh on launch
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
