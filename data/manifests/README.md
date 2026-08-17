# Manifest format

Each line is one aligned speech-to-speech utterance. Audio must be readable by
`torchaudio`; paths are relative to the project root or absolute.

```json
{"id":"que_00001","source_audio":"data/processed/que_00001.wav","target_audio":"data/targets/que_00001_es.wav","reference_translation":"Buenos días.","source_transcript":"Allin p'unchay.","speaker_id":"speaker_01","split":"train","provenance":"IWSLT Quechua-Spanish 2025"}
```

`target_audio` is mandatory for training the direct S2ST model. The IWSLT
release provides source speech and target text; generate a licensed target
Spanish waveform **offline** from its reference translation, then have a native
reviewer approve the alignment. Text is never consumed by the deployed model.

## IWSLT constrained corpus workflow

The included source corpus is at
`data/raw/iwslt_que_spa_2h/que_spa_constrained`.  Build candidates with a
separate target-audio folder, where every Spanish waveform has the matching
source file name and source split:

```powershell
python -m s2st.prepare `
  --iwslt-constrained-dir data/raw/iwslt_que_spa_2h/que_spa_constrained `
  --target-audio-dir data/targets/iwslt_que_spa_2h `
  --target-speech-generator "<licensed voice and version>" `
  --consent-id "<approved consent record>"
```

This writes `candidates.jsonl` and `native_review.csv`. Complete every review
field with a native/heritage reviewer. Only rows explicitly marked `approved`
as `yes` and backed by a real target waveform may enter a training manifest:

For approved rows, `reviewer_id` is mandatory and every review score must be an
integer from 1 to 5. This prevents anonymous or incomplete approvals from
entering the training data.

```powershell
python -m s2st.prepare `
  --iwslt-constrained-dir data/raw/iwslt_que_spa_2h/que_spa_constrained `
  --target-audio-dir data/targets/iwslt_que_spa_2h `
  --target-speech-generator "<licensed voice and version>" `
  --consent-id "<approved consent record>" `
  --approvals data/manifests/native_review.csv `
  --sync-atlas
```

The command writes `train.jsonl`, `validation.jsonl`, and `test.jsonl`, caps
total source duration at 1h40m, and checks the source-release split for speaker
leakage. If a speaker appears in more than one source split, it deterministically
re-splits by speaker instead. It stores checksums, provenance, generator,
consent, and review data in Atlas when its connection settings are configured.
Do not use `additional_mt_text` as input to the deployed speech-to-speech model.
