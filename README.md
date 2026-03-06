# AgroOS

Streamlit web app for agronomy workflows: field map, NDVI, diagnostics, operations, assistant, reports.

## Production URL (main public site)

`https://agroos-ai.streamlit.app`

## Local run (Windows PowerShell)

```powershell
cd C:\Users\astra\OneDrive\Desktop\AI_Agronom
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run main.py --server.address 127.0.0.1 --server.port 8502
```

Open: `http://localhost:8502`

## Public website for everyone (Streamlit Community Cloud)

1. Create a GitHub repository and upload this project.
2. Go to: https://share.streamlit.io/
3. Click **New app**.
4. Select your repository and branch.
5. Set **Main file path**: `main.py`
6. Click **Deploy**.

Current public URL:
`https://agroos-ai.streamlit.app`

## Push to GitHub (first time)

```powershell
cd C:\Users\astra\OneDrive\Desktop\AI_Agronom
git init
git add .
git commit -m "Initial AgroOS deploy setup"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

If the repository already exists, run only:

```powershell
git add .
git commit -m "Update AgroOS"
git push
```
