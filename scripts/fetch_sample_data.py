from datasets import load_dataset, Audio
from pathlib import Path

N_PER_CLASS = 1000

OUT_REAL = Path("test_audio/real")
OUT_SPOOF = Path("test_audio/spoof")

OUT_REAL.mkdir(parents=True, exist_ok=True)
OUT_SPOOF.mkdir(parents=True, exist_ok=True)

print("Loading ASVspoof2019 LA dataset (streaming)...")

ds = load_dataset(
    "SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA",
    split="test",
    streaming=True,
)

# IMPORTANT:
# Keep audio as raw bytes so TorchCodec is not used.
ds = ds.cast_column("audio", Audio(decode=False))

real_count = 0
spoof_count = 0

for example in ds:
    label = example["label"]
    audio_bytes = example["audio"]["bytes"]
    fname = Path(example["path"]).stem

    if label == 0 and real_count < N_PER_CLASS:
        out_path = OUT_REAL / f"{fname}.flac"
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        real_count += 1
        print(f"[real]  saved {out_path}")

    elif label == 1 and spoof_count < N_PER_CLASS:
        out_path = OUT_SPOOF / f"{fname}.flac"
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        spoof_count += 1
        print(f"[spoof] saved {out_path}")

    if real_count >= N_PER_CLASS and spoof_count >= N_PER_CLASS:
        break

print(f"\nDone. {real_count} real, {spoof_count} spoof files saved.")