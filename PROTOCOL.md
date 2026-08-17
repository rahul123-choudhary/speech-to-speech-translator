# Phase-by-phase research protocol

## 1. Scope and governance

Study the Quechua (southern varieties) speech → Spanish speech direction supported
by the IWSLT corpus. Obtain written community consent covering training, pilot
recording, retention, withdrawal, researcher access, and publication. A native
speaker review is required for every new utterance, translation, and target
speech construction decision.

## 2. Corpus preparation

Use a maximum of 1h40m of source speech for the primary small-hours condition.
Segment at utterance boundaries; reject corrupt, over-15-second, or
translation-misaligned clips. Create a speaker-disjoint 80/10/10-like split with
`python -m s2st.prepare`. Store corpus provenance, consent ID, dialect, speaker
pseudonym, source checksum, target-speech generator, and reviewer decision in
Atlas `corpus_metadata`.

## 3. Direct model adaptation

The model is XLS-R encoder + LoRA adapters + non-autoregressive Transformer
codec-unit decoder + EnCodec waveform decoder. Freeze the pretrained codec and
base encoder; optimize LoRA and decoder parameters. Apply mild speed/noise
augmentation only to source training audio. Early-stop by validation codec-unit
loss and retain the selected checkpoint.

## 4. Evaluation

On the held-out split, synthesize speech, transcribe only the generated Spanish
with a frozen, declared ASR model, and calculate sacreBLEU against target
references. This is ASR-BLEU. Record the exact ASR version, sacreBLEU signature,
checkpoint, generated waveform hash, per-utterance latency, and source duration.

Native/heritage reviewers rate each randomized, blinded sample on 1–5 scales:

| Dimension | Prompt |
| --- | --- |
| Naturalness | Does the output sound like natural Spanish speech? |
| Intelligibility | Can you understand the output without replaying it? |
| Adequacy | Does the output preserve the source meaning? |
| Cultural/contextual appropriateness | Is the rendering appropriate to the utterance and setting? |

Report mean, 95% bootstrap confidence interval, rater count, and adjudication
procedure. The API stores each authenticated reviewer rating in Atlas; export
ratings by evaluation run, compute the interval per dimension, and do not report
a single unaudited rating as a human-evaluation result. Do not compare an
ASR-BLEU score directly to text-output BLEU such as
the reported 17.7 figure without declaring the evaluation mismatch.

## 5. Live pilot

Require Firebase Authentication and explicit per-session consent. Keep Firestore
to active session state and researcher/tester profile references; use FCM only
for opted-in evaluation/session notifications. Store structured corpus metadata,
evaluation records, and consented pilot feedback in MongoDB Atlas. Do not retain
raw pilot audio by default; if approved, store its encrypted external object URL
and retention/withdrawal identifiers rather than the audio in either database.

Measure end-to-end latency from final PCM chunk to returned WAV. Report mean,
p50, and p95 separately for GPU model execution and whole-request timing.
