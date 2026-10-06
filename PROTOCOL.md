# Phase-wise research protocol

## 1. Scope and setup

The primary direction is Yorùbá speech → English speech, using the IWSLT 2026 African & Celtic speech-to-speech release. This is the selected oral-tradition language pair. Keep the source language and its varieties explicit in every manifest and report.

## 2. Data collection and preparation

The upstream Hugging Face release is about 85.3 GB. Use `scripts/fetch_iwslt_yoruba_subset.py` to obtain a small, paired subset rather than copying the full corpus. The script matches Yorùbá source IDs to English recorded-target IDs, retains audio/text/speaker metadata and checksums, and writes a candidate manifest and native-review template. Its local split is only a provisional, text-ID-disjoint split from the official training split.

Before training, a Yorùbá speaker should listen to every source/target pair, check transcript and translation fidelity, and rate intelligibility and contextual appropriateness. Record the release attribution and project-level authorization/consent basis. Only mark review rows approved when the assessment is complete. The gate in `s2st.prepare` requires both valid review ratings and authorization metadata before producing trainable manifests. For publication-quality evaluation, use the official held-out development/test data rather than the provisional training-derived partitions.

## 3. Direct model adaptation

The planned architecture is a multilingual speech encoder with parameter-efficient adaptation, a speech-unit decoder, and a vocoder. Keep the base encoder frozen initially; train adapters and decoder on the reviewed Yorùbá→English waveforms. Apply waveform augmentation only to training inputs. Select a checkpoint using validation data. This phase is not complete until the actual architecture is configured and trained on an approved corpus.

## 4. Evaluation

Evaluate generated English speech against held-out recorded English references. Use a declared English ASR system and compute ASR-based translation metrics, including BLEU/CER where appropriate. Record model/ASR versions, tokenizer and metric signatures, reference provenance, generated waveform hashes, and per-utterance latency. Do not compare speech-output ASR scores directly to text-only BLEU without describing the metric difference.

Native/heritage reviewers should rate randomized, blinded samples for naturalness, intelligibility, translation adequacy, and cultural/contextual appropriateness. Report the number of raters, mean and confidence interval per dimension, and the adjudication procedure.

## 5. Live inference and pilot

Build live Yorùbá audio input → direct speech-to-speech model → English audio output after a real checkpoint exists. Measure end-to-end latency and test with speakers. Pilot participation requires explicit per-session consent. Keep Firestore for active app/session state and MongoDB Atlas for structured corpus metadata, evaluations, and consented feedback; keep corpus audio in appropriately permissioned file/object storage.
