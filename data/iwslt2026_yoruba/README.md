# IWSLT 2026 Yorùbá→English subset

Source: [McGill-NLP/NaijaS2ST](https://huggingface.co/datasets/McGill-NLP/NaijaS2ST), revision `4fef5310ef98b8c703e490ea9908100f152ad5b3`. This is a small sample of the official training split, not a full copy of the upstream 85 GB release.

License shown on the upstream dataset card: CC BY 4.0 ([license text](https://creativecommons.org/licenses/by/4.0/)). Retain attribution and the dataset citation when using these files.

Selected 19 distinct source text IDs, 57 Yorùbá source recordings from 42 speakers, and 19 English recordings. Estimated total recorded audio: 0.35 hours (metadata duration sum). The upstream source has 15000 Yorùbá rows and 4980 source IDs with paired English rows in the scanned ranges.

All records are candidate-only. The review CSV starts with `approved=no`; native-speaker review and project-level authorization/consent must be documented before producing trainable manifests. The provisional validation and test groups are sentence-disjoint buckets drawn from the official train split, not the official IWSLT dev/test sets.
