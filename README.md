# Yorùbá Speech Translator

A small web app for recording or uploading Yorùbá speech and translating it to English. The UI, Firebase sign-in, API, and review workflow are present. A trained speech-to-speech checkpoint is not yet available, so the app cannot return model translations yet.

## Run locally

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn s2st.api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/>. Allow microphone access to record, or choose an audio file up to 45 seconds long.

## Firebase sign-in setup

The app uses Firebase Email/Password sign-in. Register a Web app in Firebase Project Settings, configure the values listed in `.env.example`, enable Email/Password in Firebase Authentication, and add `127.0.0.1` to Authorized domains. Set `FIREBASE_CREDENTIALS_PATH` to a private local Admin SDK key. Never commit or share that key. Restart the server and check `/v1/config` and `/v1/database/status`.

## Research status

- Primary research direction: Yorùbá speech → English speech, chosen for the oral-language focus and the paired-audio IWSLT 2026 African & Celtic S2S release.
- The Hugging Face link currently resolves to the expanded NaijaS2ST repository (about 85 GB). A project script can select a small, matched subset rather than copy the full release: `scripts/fetch_iwslt_yoruba_subset.py`.
- No Yorùbá corpus audio has been downloaded into this checkout yet. The script creates candidate-only manifests and an unfilled native-speaker review sheet; these do not authorize training.
- No trained model checkpoint or measured translation quality/latency result exists yet.
- MongoDB Atlas is optional in local development. `/v1/database/status` reports whether the app is connected. The Firebase browser config and server Admin SDK perform separate jobs.

See [DATASETS.md](DATASETS.md), [data/README.md](data/README.md), and [PROTOCOL.md](PROTOCOL.md) for acquisition, review gates, and research methodology.
