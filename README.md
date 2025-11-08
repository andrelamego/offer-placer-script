# Eldorado Offer Placer

A complete automation tool for creating and publishing **offers (brainrots)** on [Eldorado.gg](https://www.eldorado.gg), built with **Python + Selenium + CustomTkinter**.

The project provides a clean, modern GUI to manage product insertions — allowing you to create new offer batches, automatically fill the website forms, and keep timestamped CSV logs of every insertion made.

---

## Features

- **Modern GUI (CustomTkinter)**
  - Sidebar navigation with **Add Offers** and **Configs** screens.
  - “Add Brainrots” form with validation and optional default description.
- **Automated Posting (Selenium + undetected_chromedriver)**
  - Automatically opens Chrome with your saved profile.
  - Pauses for manual login with confirmation popup.
  - Publishes all offers listed in the active `.csv` file.
- **Insertion System**
  - Each insertion is a batch of offers inside one CSV (`data/itens.csv`).
  - Previous insertions are saved automatically as timestamped logs (`data/logs/`).
- **Smart Form**
  - If a brainrot with the same name already exists, quantity is incremented instead of duplicated.
  - Checkbox to use or disable a default description.
  - Strict field validation (integer quantity, decimal price).
- **Persistent Settings**
  - Saves Chrome profile path and default description in `data/config.json`.
  - Buttons to reset to defaults or save configuration.

---

## Installation

Requirements
- Python 3.10+
- Google Chrome installed
- Compatible ChromeDriver (handled automatically via undetected_chromedriver)

Clone this repository and install dependencies:

```bash
git clone https://github.com/andrelamego/offer-placer-script.git
cd offer-placer-script

pip install -r requirements.txt
```

---

## Tech Stack

| Category       | Technology                                                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| GUI            | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)                                                                  |
| Web Automation | [Selenium](https://www.selenium.dev/) + [undetected_chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) |
| Data Handling  | Python CSV module                                                                                                                |
| Configuration  | JSON                                                                                                                             |
| Logging        | Console + GUI Textbox                                                                                                            |

---

## Author

**André Lamego**
*Eldorado Offer Placer Bot — Smart Offer Automation*
- GitHub: @andrelamego
- Email: andreolamego@gmail.com

---

## 🌟 Roadmap / Future Improvements

- Implement “Add by Image” mode (automatic image scanning).
- Detailed report generation after each insertion.
