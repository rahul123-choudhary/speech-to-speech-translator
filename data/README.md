# Data directory

The active research pair is Yorùbá speech → English speech. The project's compact IWSLT/NaijaS2ST downloader and current dataset status are documented in [DATASETS.md](../DATASETS.md).

The full upstream release is about 85.3 GB and is not copied into this project. To fetch a review-gated subset, run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_iwslt_yoruba_subset.py --hours 2
```

That command writes raw audio and candidate/review files to `data/iwslt2026_yoruba/`. All candidates remain unapproved until Yorùbá speaker review and project authorization are documented. Do not upload raw audio to Firebase or MongoDB; the databases are for app/session and structured research metadata, not corpus storage.
