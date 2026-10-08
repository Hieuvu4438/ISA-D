# Local speech milestone 08/10/2026

- RED: local provenance contract failed Pydantic validation; frontend95s deadline regression test failed at30s. Checkpoint5599998.
- GREEN:119 backend tests PASS;50 speech/config/budget/contract tests PASS; Ruff PASS. Coverage before8 added config tests:85% combined, local recognizer97%; not evidence of80% branch everywhere.
- Frontend lint/typecheck/17unit/build PASS.
- Actual local Whisper-small CPU INT8:5/5 FLEURS WAV recognized,22/126 word edits (17.46% WER),6.45–9.60s/sample during concurrent test activity. Raw evidence speech-local-check.json contains immutable model/file hashes, source references and transcripts.
- Production browser E2E: `npx playwright test e2e/local-speech.spec.ts --reporter=list,json`, with LOCAL_SPEECH_E2E_AUDIO firstFLEURS WAV and ignored runtime Playwright browsers.1/1PASS in6.1s, no mocks or Azurecalls. Transcript upload→response200/local→UI text→manual edit→voice search provenance checked. This is actual prerecorded human audio, not user microphone speech acceptance.
- npm audit omitdev0 findings; pip-audit no known findings for lockfile, torchCPU skipped because wheel not on PyPI. Azure calls0/5; prior auth check401 remains unresolved.
- Model/runtime/.env ignored; application startup does not download speech weights. No automatic cloud fallback or request retries.
- Current full app quality limits remain as previous DELIVERY_STATUS (2 ranking quality tests fail; independent60query gate not finished). Local speech addition does not erase those findings.
