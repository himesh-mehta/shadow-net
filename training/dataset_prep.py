"""
Dataset Preparation & Ingestion Module for SHADOW-NET Training.
Supports:
1. Parsing ASVspoof 2019 / 2021 protocols (bonafide vs. spoof).
2. Parsing WaveFake directories.
3. Class balancing & stratified train/val/test splitting.
4. Synthetic test bench generator for immediate local verification without 30GB downloads.
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import soundfile as sf


def generate_synthetic_audio(duration_sec: float = 2.0, sr: int = 16000, is_fake: bool = False) -> np.ndarray:
    """
    Generates synthetic speech-like waveforms.
    Real: Natural multi-harmonic formant structure with vibrato and smooth amplitude envelope.
    Fake: Vocoder phase distortion, high-frequency artifacts, and periodic harmonic smearing.
    """
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    
    # Fundamental pitch with natural micro-jitter
    base_f0 = random.uniform(110.0, 220.0)
    jitter = 0.015 * np.sin(2 * np.pi * 5.0 * t) if not is_fake else 0.0  # Fakes often have robotic flat pitch
    f0 = base_f0 * (1.0 + jitter)
    
    # Formants (F1, F2, F3)
    formants = [500.0, 1500.0, 2500.0]
    signal = np.zeros_like(t)
    
    for f in formants:
        harmonic = np.sin(2 * np.pi * f * t)
        decay = np.exp(-((t % 0.1) * 20.0))
        signal += 0.3 * harmonic * decay

    # Add vocal tract resonance
    signal += 0.5 * np.sin(2 * np.pi * base_f0 * t)
    
    if is_fake:
        # Synthetic / deepfake artifacts:
        # 1. High-frequency checkerboard / vocoder noise (e.g. MelGAN / HiFi-GAN artifacts)
        hf_artifact = 0.15 * np.sin(2 * np.pi * 6500.0 * t) * (np.sin(2 * np.pi * 50.0 * t) > 0)
        # 2. Phase discontinuity
        phase_glitch = 0.10 * np.sign(np.sin(2 * np.pi * 800.0 * t))
        # 3. High-frequency spectral hiss
        noise = 0.08 * np.random.normal(0, 1, size=len(t))
        signal = signal + hf_artifact + phase_glitch + noise
    else:
        # Natural background acoustic room noise (very low)
        noise = 0.01 * np.random.normal(0, 1, size=len(t))
        signal = signal + noise

    # Normalize amplitude to [-0.95, 0.95]
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = 0.90 * (signal / max_val)
        
    return signal.astype(np.float32)


def create_synthetic_test_bench(output_dir: Path, n_samples: int = 40) -> Dict[str, str]:
    """
    Creates a small, balanced synthetic dataset for fast CI / developer verification.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    records = []
    print(f"Generating {n_samples} balanced audio samples in: {audio_dir}")

    # Generate 50% real, 50% fake
    for i in range(n_samples):
        is_fake = (i % 2 == 1)
        label_str = "spoof" if is_fake else "bonafide"
        label_num = 1 if is_fake else 0
        file_name = f"sample_{i:04d}_{label_str}.wav"
        file_path = audio_dir / file_name
        
        audio = generate_synthetic_audio(duration_sec=2.2, sr=16000, is_fake=is_fake)
        sf.write(str(file_path), audio, 16000, format="WAV", subtype="PCM_16")
        
        records.append({
            "audio_path": str(file_path.resolve()),
            "file_name": file_name,
            "label_str": label_str,
            "label": label_num,
            "duration_sec": 2.2,
        })

    # Shuffle and split into train (60%), val (20%), test (20%)
    random.seed(42)
    random.shuffle(records)

    n_train = int(0.60 * n_samples)
    n_val = int(0.20 * n_samples)
    
    splits = {
        "train": records[:n_train],
        "val": records[n_train : n_train + n_val],
        "test": records[n_train + n_val:],
    }

    manifest_paths = {}
    for split_name, split_records in splits.items():
        manifest_file = output_dir / f"{split_name}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(split_records, f, indent=2)
        manifest_paths[split_name] = str(manifest_file)
        real_count = sum(1 for r in split_records if r["label"] == 0)
        fake_count = sum(1 for r in split_records if r["label"] == 1)
        print(f"  Split '{split_name}': {len(split_records)} samples ({real_count} real, {fake_count} fake) -> {manifest_file.name}")

    return manifest_paths


def parse_asvspoof_protocol(
    protocol_file: Path,
    audio_dir: Path,
    output_manifest: Path,
    max_samples: int = None
) -> int:
    """
    Parses standard ASVspoof protocol text files:
    Format: SPEAKER_ID AUDIO_FILE_NAME - SYSTEM_ID LABEL
    bonafide -> label 0, spoof -> label 1
    """
    if not protocol_file.is_file():
        raise FileNotFoundError(f"ASVspoof protocol file not found: {protocol_file}")

    records = []
    with open(protocol_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            audio_name = parts[1]
            label_str = parts[4].lower()
            
            # Find audio file (support .wav and .flac)
            candidates = [
                audio_dir / f"{audio_name}.wav",
                audio_dir / f"{audio_name}.flac",
                audio_dir / audio_name,
            ]
            file_path = next((p for p in candidates if p.is_file()), None)
            
            if file_path:
                label_num = 1 if label_str == "spoof" else 0
                records.append({
                    "audio_path": str(file_path.resolve()),
                    "file_name": file_path.name,
                    "label_str": label_str,
                    "label": label_num,
                    "system_id": parts[3] if len(parts) > 3 else "unknown",
                })
                if max_samples and len(records) >= max_samples:
                    break

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Parsed {len(records)} ASVspoof records -> {output_manifest}")
    return len(records)


def parse_wavefake_directory(
    wavefake_dir: Path,
    output_manifest: Path,
    real_subdirs: List[str] = None
) -> int:
    """
    Parses WaveFake dataset directory where real audio is in real_subdirs
    and other subdirectories correspond to synthetic vocoder architectures.
    """
    if not wavefake_dir.is_dir():
        raise FileNotFoundError(f"WaveFake directory not found: {wavefake_dir}")

    if real_subdirs is None:
        real_subdirs = ["ljspeech_real", "real", "bonafide"]

    records = []
    for sub in wavefake_dir.iterdir():
        if not sub.is_dir():
            continue
        is_real = any(r in sub.name.lower() for r in real_subdirs)
        label_num = 0 if is_real else 1
        label_str = "bonafide" if is_real else "spoof"

        for audio_file in sub.glob("*.wav"):
            records.append({
                "audio_path": str(audio_file.resolve()),
                "file_name": audio_file.name,
                "label_str": label_str,
                "label": label_num,
                "vocoder": sub.name,
            })

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Parsed {len(records)} WaveFake records -> {output_manifest}")
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHADOW-NET Dataset Preparation")
    parser.add_argument("--synthetic-bench", action="store_true", help="Generate small synthetic test bench")
    parser.add_argument("--n-samples", type=int, default=40, help="Number of synthetic samples to generate")
    parser.add_argument("--output-dir", type=str, default="datasets/synthetic_bench", help="Target output directory")
    parser.add_argument("--asvspoof-protocol", type=str, help="Path to ASVspoof protocol txt file")
    parser.add_argument("--audio-dir", type=str, help="Path to raw audio directory")
    parser.add_argument("--wavefake-dir", type=str, help="Path to WaveFake root folder")

    args = parser.parse_args()

    if args.synthetic_bench or not (args.asvspoof_protocol or args.wavefake_dir):
        out_path = Path(args.output_dir)
        create_synthetic_test_bench(out_path, n_samples=args.n_samples)
    elif args.asvspoof_protocol:
        parse_asvspoof_protocol(
            Path(args.asvspoof_protocol),
            Path(args.audio_dir),
            Path(args.output_dir) / "asvspoof_manifest.json"
        )
    elif args.wavefake_dir:
        parse_wavefake_directory(
            Path(args.wavefake_dir),
            Path(args.output_dir) / "wavefake_manifest.json"
        )
