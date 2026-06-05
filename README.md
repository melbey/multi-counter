# Multi Counter Clicker - online Google Sheets version

This Streamlit app stores counters in a Google Sheet through a Google Apps Script backend.

It avoids Google Cloud service account JSON keys.

## Files

Upload these files to a GitHub repo:

- `multi_counter_gsheets.py`
- `requirements.txt`
- `README.md`

Use `multi_counter_gsheets.py` as the main Streamlit file.

## 1. Google Sheet + Apps Script

1. Create a new Google Sheet, for example `Multi Counter Data`.
2. Open it.
3. Go to Extensions -> Apps Script.
4. Replace `Code.gs` with the `Code.gs` file from this ZIP.
5. Change:

```js
API_TOKEN: "CHANGE_ME_TO_A_PRIVATE_RANDOM_TOKEN"
```

to a private random token.

6. Save.
7. Deploy -> New deployment.
8. Select type: Web app.
9. Execute as: Me.
10. Who has access: Anyone with the link.
11. Deploy and copy the Web app URL.

## 2. Streamlit secrets

In Streamlit Cloud, add:

```toml
APPS_SCRIPT_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
APPS_SCRIPT_TOKEN = "the same private token from Code.gs"
```

Do not share your token.

## 3. Importing old local data

The import tool accepts your old local Multi Counter JSON format:

```json
[
  {"name": "Counter", "count": 0}
]
```

It also accepts the newer online format with IDs.
