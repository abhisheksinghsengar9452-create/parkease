# Phase 6 — ANPR

Install optional local OCR dependencies when a compatible camera is ready:

```powershell
pip install opencv-python easyocr numpy
```

OCR output is never treated as authorization to open a barrier. Invalid or
low-confidence readings require manual review. Repeated reads are suppressed for
the configured cooldown period before any parking business action is considered.
