# Dataset decision: Quechua → Spanish

## Primary small-hours corpus

Use the public [IWSLT 2025 Quechua–Spanish release](https://github.com/Llamacha/IWSLT2025_Quechua_data).
Its maintainers state that it provides **1 hour 40 minutes** of Quechua audio
aligned to Spanish translations. It uses southern Quechua varieties and is
licensed CC BY-NC-ND 3.0. This directly supports the requested minimal-hours
condition (roughly two hours), but it provides source speech + target text, not
paired target speech.

To train the direct audio-unit decoder, produce a reviewable target Spanish
speech side from the provided target translations using a research-licensed
Spanish voice. Keep the source corpus provenance and the target-speech generator
version per utterance in MongoDB. This is an offline data-construction step;
the trained model itself has no text path at deployment.

## Additional/unconstrained data

The same IWSLT release describes approximately 48 hours of fully transcribed
Quechua audio (Siminchik) and roughly 8 hours from Huqariq with post-edited
machine-generated Spanish translations. These must be reported as an
**unconstrained** condition, separate from the 1h40m primary experiment.

Mozilla Common Voice lists multiple Quechua varieties, including Puno Quechua
(qxp) and Southern Pastaza Quechua (qup), under CC0. Use only a dialect matched
to the intended community and only for separately labelled ASR/encoder
adaptation; it is not aligned Quechua–Spanish translation data.

## Why this direction

The public aligned corpus is Quechua speech → Spanish translation. Reversing it
to Spanish speech → Quechua speech would require real Quechua target-speech
recordings aligned to Spanish; synthetic Quechua targets should not be presented
as community-grounded preservation data. A community-collected reciprocal corpus
is required before claiming Spanish → Quechua speech output.

## Citations

- IWSLT Quechua–Spanish data release, Llamacha / Siminchikkunarayku.
- Zevallos et al. (2022), *Huqariq: A Multilingual Speech Corpus of Native
  Languages of Peru for Speech Recognition*.
- Cárdenas et al. (2018), *Siminchik: A speech corpus for preservation of
  southern Quechua*.

