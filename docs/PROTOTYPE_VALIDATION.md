# Prototype validation — 1 November 2026

This document separates software checks from speech-classification evidence.
It is not an accuracy certification. The user's original local recordings were not
available in this environment and have not been tested.

## Software checks

- Frontend production build: Next.js 14.2.35, compilation and TypeScript checks passed. All nine application routes returned HTTP 200 from a started production server.
- Eleven regression tests cover explicit class-label mapping, demo behavior, persisted
  mode overrides, failed model loading, REST/SSE agreement, silence rejection,
  decision-score consistency, WebSocket heartbeats and analysis, evaluation class
  counting, duplicate-tail prevention, best/last checkpoints and unreadable training files.
- Real HTTP API smoke check used the selected pretrained weights: health showed the
  correct revision; seeded login, session creation, SSE analysis, two incident records,
  four timeline entries, and ML-to-demo switching passed.
- Mock MongoDB was used, not a persistent MongoDB deployment.
- A browser automation check was attempted, but the available Chromium binary could not be downloaded. Build checks and API tests do not replace manual browser testing.
- Dependency deprecation warnings remain. The checkpoint regression test mocks the
  optimizer/training step, causing a scheduler-order warning in that test; it does
  not train a model or evaluate classification accuracy.

## Candidate comparison

Both candidates were downloaded as safetensors from pinned revisions and run using
their own 16 kHz feature extractors on CPU. No thresholds were tuned to these clips.

| Candidate | Result on these four clips | Decision |
|---|---|---|
| MelodyMachine/Deepfake-audio-detection-V2 | Both generated clips and both human clips labeled REAL | Rejected as default |
| Gustking/wav2vec2-large-xlsr-deepfake-audio-classification | Two generated clips AI_SUSPECTED; two human clips REAL | Selected provisionally |

The selected model's publisher lists Apache-2.0 and reports evaluation on an
ASVspoof2019 subset. The card does not fully specify its training corpus or language
coverage. None of its published metrics are represented as this project's metrics.

## Observed live-API outputs

Clips came from Gary Stafford's public `deepfake-audio-detection` dataset. Its card
labels `el_` files as ElevenLabs-generated and `yt_` files as human YouTube speech.
The two human clips are from one source group and the two AI clips from another.
They are not four independent speakers. Overlap with model training is unknown.

| Clip | Dataset label | API verdict | Aggregate AI score | Analysis time on this host |
|---|---|---|---:|---:|
| fake/el_0001_c_part_002.flac | Generated | AI_SUSPECTED | 0.8853 | 1.46 s |
| fake/el_0001_c_part_003.flac | Generated | AI_SUSPECTED | 0.8804 | 1.14 s |
| real/yt_0000_p2_part_167.flac | Human | REAL | 0.0820 | 2.75 s |
| real/yt_0000_part_001.flac | Human | REAL | 0.1090 | 2.17 s |

These are uncalibrated scores, not probabilities of factual authenticity. Analysis
uses 4-second windows with a 2-second hop and the original max/mean aggregation.
The source recordings are not bundled. Raw observations and the rejected candidate's
results are preserved in [model_smoke_results.json](model_smoke_results.json).

## Still needed on the student's computer

- Install the provided source and download the pinned weights once (approximately 1.3 GB).
- Test the student's actual human and generated recordings, retaining failures.
- Test microphone permissions, WAV capture, and CPU responsiveness in the local browser.
- Use more speakers, generators, recording conditions and relevant languages before
  presenting any accuracy estimate. Keep final evaluation examples separate from
  examples used to choose the model or thresholds.
- A local CPU may be slower than this host. Do not promise real-time interception.

## Sources and attribution

- Selected model and configuration: https://huggingface.co/Gustking/wav2vec2-large-xlsr-deepfake-audio-classification
- Selected revision: `f7050b586236dc910d1157f430def2d0647b02b4`
- Rejected candidate: https://huggingface.co/MelodyMachine/Deepfake-audio-detection-V2
- Rejected revision: `de3cde5a29c449bb5268814e421b46bf6ebdcd72`
- Speech smoke-test dataset: https://huggingface.co/datasets/garystafford/deepfake-audio-detection
- Waveform preprocessing documentation: https://huggingface.co/docs/transformers/en/model_doc/wav2vec2
