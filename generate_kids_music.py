import argparse
import math
import random
import wave
from pathlib import Path

SAMPLE_RATE = 22050
TEMPO = 120
BEAT = 60.0 / TEMPO
STEP = BEAT / 2.0

SCALE = [60, 62, 64, 67, 69, 72, 74, 76]
CHORDS = [
    [60, 64, 67],
    [65, 69, 72],
    [67, 71, 74],
    [60, 64, 67],
]

random.seed(42)


def midi_freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def envelope(local_time, duration):
    attack = 0.025
    release = 0.12

    if local_time < attack:
        return local_time / attack

    if local_time > duration - release:
        return max(0.0, (duration - local_time) / release)

    return 1.0


def synth_sample(t, step_index, duration):
    beat_index = int(t / BEAT)
    bar_index = beat_index // 4
    local_beat = t - beat_index * BEAT
    step_local = t - step_index * STEP

    chord = CHORDS[(bar_index // 2) % len(CHORDS)]

    # Pad léger
    pad = 0.0
    for note in chord:
        freq = midi_freq(note)
        pad += math.sin(2.0 * math.pi * freq * t)
    pad /= len(chord)

    # Basse
    bass_note = chord[0] - 12
    bass = math.sin(2.0 * math.pi * midi_freq(bass_note) * t)

    # Mélodie pentatonique
    pattern = [0, 1, 2, 4, 2, 1, 0, 4]
    note_index = pattern[step_index % len(pattern)]
    melody_note = SCALE[(note_index + bar_index) % len(SCALE)]

    rest = (step_index % 8 == 7)
    melody = 0.0

    if not rest:
        freq = midi_freq(melody_note)
        melody = math.sin(2.0 * math.pi * freq * t)
        melody += 0.30 * math.sin(4.0 * math.pi * freq * t)

    mel_env = envelope(step_local, STEP)

    # Kick
    kick = 0.0
    if local_beat < 0.12:
        x = local_beat / 0.12
        freq = 100.0 - 60.0 * x
        kick = math.sin(2.0 * math.pi * freq * local_beat)
        kick *= math.exp(-18.0 * local_beat)

    # Clap
    clap = 0.0
    beat_in_bar = beat_index % 4
    if beat_in_bar in (1, 3) and local_beat < 0.08:
        noise = random.uniform(-1.0, 1.0)
        clap = noise * math.exp(-35.0 * local_beat)

    # Hi-hat
    hat = 0.0
    half_step = step_index % 2
    if half_step == 1 and step_local < 0.035:
        noise = random.uniform(-1.0, 1.0)
        hat = noise * math.exp(-90.0 * step_local)

    value = (
        pad * 0.050
        + bass * 0.045
        + melody * 0.105 * mel_env
        + kick * 0.14
        + clap * 0.035
        + hat * 0.018
    )

    # Petite montée d'énergie cyclique
    cycle = int(t / 16.0) % 4
    if cycle == 1:
        value *= 1.05
    elif cycle == 2:
        value *= 1.10
    elif cycle == 3:
        value *= 0.95

    return max(-0.75, min(0.75, value))


def generate(output_path, duration):
    total_samples = int(duration * SAMPLE_RATE)
    block_size = 22050

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        written = 0

        while written < total_samples:
            count = min(block_size, total_samples - written)
            frames = bytearray()

            for i in range(count):
                sample_index = written + i
                t = sample_index / SAMPLE_RATE
                step_index = int(t / STEP)

                value = synth_sample(
                    t,
                    step_index,
                    duration,
                )

                # Fade in / out
                if t < 1.5:
                    value *= t / 1.5

                remaining = duration - t
                if remaining < 2.0:
                    value *= max(0.0, remaining / 2.0)

                sample = int(value * 32767)
                frames += int(sample).to_bytes(
                    2,
                    byteorder="little",
                    signed=True,
                )

            wav.writeframes(frames)
            written += count

            progress = int((written / total_samples) * 100)
            if progress % 10 == 0 and written < total_samples:
                print(f"🎵 Musique : {progress}%")

    print(f"✅ Musique créée : {output_path}")
    print(f"⏱️ Durée : {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=300.0)
    args = parser.parse_args()

    generate(
        args.output,
        args.duration,
    )


if __name__ == "__main__":
    main()
