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

from time import sleep

repeat = False

async def speak(text):
    tts = edge_tts.Communicate(text=text, voice="en-US-AriaNeural")

    temp_file = os.path.join(tempfile.gettempdir(), "temp_tts.wav")
    await tts.save(temp_file)

    data, samplerate = sf.read(temp_file)
    sd.play(data, samplerate=samplerate, blocking=True)

    os.remove(temp_file)

def run_speak_async(text):
    # Run the async speak in a separate thread to avoid blocking
    asyncio.run(speak(text))

def flush_input():
    while msvcrt.kbhit():
        msvcrt.getch()

def main():
    global repeat

    os.system('cls')

    while True:
        try:
            difficulty = int(input('> Choose a difficulty.\n> 1: Advanced\n> 2: Expert\n> '))
            if difficulty == 1:
                file = 'advanced.txt'
            elif difficulty == 2:
                file = 'expert.txt'
            break
        except:
            pass

    with open(file, 'r') as f:
        words = f.readlines()
        words = [word for word in words if not word.startswith('--') and word.replace('\n', '') != ''] # Remove comments and gaps

    words_guessed = []

    while True:
        os.system('cls')

        if len(words_guessed) == len(words):
            words_guessed.clear()

            tts_thread = threading.Thread(target=run_speak_async, args=('Great job!',))
            tts_thread.start()

            print("> You guessed all of the words correctly, restarting the game...")
            tts_thread.join()  # Wait until tts is done

            os.system('cls')

        if not repeat:
            while True:
                word = random.choice(words).strip().replace('- ','')
                if word in words_guessed:
                    continue
                else:
                    break
            start_lines = ['Can you spell', 'The next word is', 'Alright, spell', 'Your word is', 'Spell']
            text_to_speak = f'{random.choice(start_lines)}, {word}'
        else:
            repeat = False
            text_to_speak = word

        # Start TTS thread and wait for it to finish before timing input
        tts_thread = threading.Thread(target=run_speak_async, args=(text_to_speak,))
        tts_thread.start()
        tts_thread.join()  # Wait until tts is done

        flush_input() # Any buffered keys will be cleared before the input

        # WPM Calculation
        start_time = time.time()
        userinput = input('> ')
        end_time = time.time()

        if userinput.lower() in ['repeat', 'r']:
            repeat = True
            continue

        if userinput.lower() == word.lower():
            os.system('cls')
            words_guessed.append(word)
            elapsed_minutes = (end_time - start_time) / 60
            wpm = (len(userinput) / 5) / elapsed_minutes if elapsed_minutes > 0 else 0
            print(f"> Correct, the answer was {word}!", f'{len(words_guessed)}/{len(words)}')
            print(f"> Your typing speed: {wpm:.2f} WPM")
            asyncio.run(speak("Correct!"))
            sleep(0.5)
        else:
            print(f"> Incorrect, the answer was: {word}", f'{len(words_guessed)}/{len(words)}')
            asyncio.run(speak("Incorrect!"))
            sleep(1.5)

if __name__ == "__main__":
    main()
