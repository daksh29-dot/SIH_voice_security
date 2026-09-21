from datasets import load_dataset, Audio
from pathlib import Path

N_NEW_PER_CLASS = 200

OUT_REAL = Path("test_audio/real")
OUT_SPOOF = Path("test_audio/spoof")

OUT_REAL.mkdir(parents=True, exist_ok=True)
OUT_SPOOF.mkdir(parents=True, exist_ok=True)

# Existing files
existing_real = {p.stem for p in OUT_REAL.glob("*.flac")}
existing_spoof = {p.stem for p in OUT_SPOOF.glob("*.flac")}

print(f"Existing real:  {len(existing_real)}")
print(f"Existing spoof: {len(existing_spoof)}")

print("\nLoading ASVspoof2019 LA dataset (streaming)...")

ds = load_dataset(
    "SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA",
    split="test",
    streaming=True,
)

# Keep raw bytes — avoids TorchCodec
ds = ds.cast_column("audio", Audio(decode=False))

real_count = 0
spoof_count = 0

for example in ds:

    label = example["label"]
    audio_bytes = example["audio"]["bytes"]
    fname = Path(example["path"]).stem

    # ---------------- REAL ----------------
    if (
        label == 0
        and fname not in existing_real
        and real_count < N_NEW_PER_CLASS
    ):
        out_path = OUT_REAL / f"{fname}.flac"

        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        existing_real.add(fname)
        real_count += 1

        print(f"[real]  saved {out_path}")

    # ---------------- SPOOF ----------------
    elif (
        label == 1
        and fname not in existing_spoof
        and spoof_count < N_NEW_PER_CLASS
    ):
        out_path = OUT_SPOOF / f"{fname}.flac"

        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        existing_spoof.add(fname)
        spoof_count += 1

        print(f"[spoof] saved {out_path}")

    # Stop after getting the requested NEW samples
    if (
        real_count >= N_NEW_PER_CLASS
        and spoof_count >= N_NEW_PER_CLASS
    ):
        break

print("\nDone.")
print(f"New real files:  {real_count}")
print(f"New spoof files: {spoof_count}")

print(f"Total real files:  {len(list(OUT_REAL.glob('*.flac')))}")
print(f"Total spoof files: {len(list(OUT_SPOOF.glob('*.flac')))}")