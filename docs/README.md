### 1. Create `config.txt`

```txt
--store-cache=C:\Users\z\AppData\Roaming\heroic\store_cache
--output=index.html
--steam-user=xxxx
--openai-api-key=xxxx
```

Replace `xxxx` with your actual Steam username and API key.

---

### 2. Build the HTML Report

Run the script (it may take a while to fetch and cache game data):

```bash
python3 game_report_html.py @config.txt
```

This generates `index.html`.

---

### 3. Encrypt with Staticrypt

Install Staticrypt if you haven’t:

```bash
npm install -g staticrypt
```

Then run:

```powershell
.\node_modules\.bin\staticrypt.ps1 index.html -d ./docs -p "CHANGEPASSWORD" --short --remember 30 --template-title "Zobair's Game Library" --template-instructions 'For Zobair&rsquo;s eyes only. <a href="./sample.html" target="_blank">View preview</a>' --template-placeholder "Enter secret passphrase" --template-button "Unlock Library" --template-error "Access denied. Try again." --template-color-primary "#0d6efd" --template-color-secondary "#f8f9fa"
```

The encrypted report will be saved in `./docs`.
