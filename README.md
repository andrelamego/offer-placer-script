# 🪙 Eldorado Offer Placer

**Eldorado Offer Placer** is a complete automation tool for creating and publishing offers (*brainrots*) on [Eldorado.gg](https://www.eldorado.gg), built with **Python + Selenium + CustomTkinter**.

It provides a **modern, elegant GUI** and full automation for posting offers — from creation to publishing — all while managing CSV logs and validating license keys securely.

---

##  Features

###  Modern GUI (CustomTkinter)
- Sidebar navigation with **Add Offers** and **Configs** screens.  
- “**Add Brainrots**” form with validation and optional default description.  
- Persistent settings saved locally in `data/config.json`.  
- Non-editable log console inside the app.

###  Automated Posting (Selenium + undetected_chromedriver)
- Launches Chrome using your saved profile automatically.  
- **Login confirmation popup** before continuing automation.  
- Posts all offers found in the active `.csv` file seamlessly.

###  Insertion System
- Each insertion is a **batch of offers** inside one CSV (`data/itens.csv`).  
- Previous insertions are archived automatically in timestamped logs (`data/logs/`).  
- **Smart merge:** if a brainrot with the same name already exists, its quantity is incremented instead of duplicated.

###  Smart Form
- Checkbox to enable or disable the **default description**.  
- Strict input validation:
  - Quantity → integers only  
  - Price → decimals only  

###  Persistent Settings
- Save and reload:
  - Chrome profile path  
  - Default offer description  
- Buttons to reset to default or save configuration changes.

###  License Key System (API Integration)
- License-based activation through an external API ([license-api](github.com/andrelamego/license-api)).  
- Automatically registers your device (`consumer_id`) on first use.  
- Each key becomes bound to one device upon activation.  
- On startup, the app verifies key validity before running.

---

##  Installation

### Requirements
- Python **3.10+**  
- **Google Chrome** installed  
- Compatible **ChromeDriver** (handled automatically via `undetected_chromedriver`)

### Setup
Clone this repository and install dependencies:

```bash
git clone https://github.com/andrelamego/offer-placer-script.git
cd offer-placer-script

pip install -r requirements.txt
```

##  Tech Stack

|Category|Technology|
|---|---|
|GUI|CustomTkinter|
|Web Automation|Selenium + undetected_chromedriver|
|Data Handling|Python CSV module|
|Configuration|JSON|
|Logging|Console + GUI Textbox|
|License Management|FastAPI + PostgreSQL (Railway)|

---

##  Roadmap / Future Improvements

-  Implement “Add by Image” mode (automatic image scanning).
    
-  Generate detailed reports after each insertion.
    
-  Cloud sync for settings and logs.
    
-  Multi-user license dashboard (admin panel).
    

---

## 🪪 License

This project is distributed under a **Dual License Model**:

### 🔹 Open Source (MIT License)
You are free to use, modify, and distribute this software for **personal or educational** purposes, under the standard terms of the [MIT License](LICENSE).

### 🔸 Commercial Use (Proprietary License)
Any **commercial use**, resale, or integration into paid products, SaaS platforms, or closed-source systems **requires a commercial license agreement** with the author.

For commercial inquiries or licensing requests, please contact:

📧 **andreolamego@gmail.com**  
🐙 **[@andrelamego](https://github.com/andrelamego)**

---

**Summary:**

| ✅ Allowed (MIT) | ❌ Restricted (Commercial) |
|------------------|----------------------------|
| Personal use | Selling or reselling the app |
| Educational use | Integration into paid tools |
| Forks and open contributions | Removing license validation |
| Custom modifications | Rebranding or closed-source redistribution |

---

© 2025 **André Lamego** — *Eldorado Offer Placer*  
Licensed under **Dual License (MIT + Proprietary)**  
Commercial use requires explicit authorization.
