# GCP + Claude Code (Vertex AI) - Troubleshooting

## Kad Claude Code "vrti" i ne daje odgovor

Najčešći uzrok: istekla Google autentifikacija (RAPT token).

### Quick fix
```bash
gcloud auth login --update-adc
```
Nakon toga restartaj VS Code ako ne proradi odmah.

---

## Korisne naredbe

### Autentifikacija
```bash
# Provjeri s kojim računom si ulogiran
gcloud auth list

# Login + osvježi Application Default Credentials (ADC)
gcloud auth login --update-adc

# Samo osvježi ADC (bez ponovnog logina)
gcloud auth application-default login
```

### Projekt
```bash
# Koji projekt je aktivan
gcloud config get-value project

# Promijeni projekt
gcloud config set project ht-gcp-ai-olimp-dev
```

### VM instance
```bash
# Lista VM-ova
gcloud compute instances list

# SSH na olimp-test-vm
gcloud compute ssh olimp-test-vm --zone=europe-west3-c
```

### Testiranje veze s Claude API-jem (Vertex AI)
```bash
# Provjeri da li ADC radi
gcloud auth application-default print-access-token

# Test Vertex AI endpoint
curl -s -w "%{http_code}" -o /dev/null \
  "https://europe-west3-aiplatform.googleapis.com/v1/projects/ht-gcp-ai-olimp-dev/locations/europe-west3/publishers/anthropic/models/claude-sonnet-4-20250514:predict" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)"
```

---

## Tipični error poruke

| Error | Uzrok | Fix |
|---|---|---|
| `invalid_rapt` | Istekla RAPT re-auth policy | `gcloud auth login --update-adc` |
| `Reauthentication required` | Istekla sesija | `gcloud auth login` |
| `Could not automatically determine credentials` | ADC nije postavljen | `gcloud auth application-default login` |
| Vrti bez odgovora u Claude Code | Najčešće istekli ADC | `gcloud auth login --update-adc` + restart VS Code |
