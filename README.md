# 👻 Snapchat Memories Master Organizer & Restorer

> **The ultimate cross-platform solution to clean up, restore, and organize raw Snapchat memories exports. Automatically merges overlay stickers, renames files by true timestamps, restores GPS & EXIF metadata to work on IOS and Android ,,, and sorts everything into clean yearly folders.**
> 
> *Done by: KBJ911*

---

## 🌟 Overview

When you download your data export from Snapchat, you are left with a chaotic archive: 
* Files have random IDs instead of proper dates.
* Overlays, stickers, and captions are detached as separate transparent PNGs.
* GPS locations and exact capture times are trapped inside history files. The only one to work on both IOS and Android ✅ at same time.

**Snapchat Memories Master Organizer** automates the entire cleanup:
* **Re-merges** overlay stickers and captions back onto their original photos and videos.
* **Restores** true chronological timestamps and renames files accordingly (e.g., `2020-12-04-16-45-50.mp4`).
* **Injects** correct GPS and EXIF metadata so map pins work properly across iOS and Android.
* **Organizes** everything into clean, structured yearly folders (`Snapchat-YYYY`).

*✨ **Tested & Proven:** Successfully executed with 100% efficiency on **Windows** and **Android (Termux)**.*

---

## 💡 Usage Tips & Convenience

### 🪟 On Windows (PC):
* You can easily **drag and drop** your raw Snapchat folder or ZIP file directly into the terminal when prompted, or type its path. 
* The tool automatically generates the organized output folder right next to your source location.

### 📱 On Android (Termux):
* **Best Practice:** To avoid typing long storage paths, place your ZIP file or extracted folder directly in the **same directory** as the script.
* Simply type the folder or file name when prompted, and it will automatically detect and process everything!

---

## 📋 System Requirements & Performance Advice

* **Python:** Version **3.8 or higher** (Python 3.8+).
* **FFmpeg:** Automatically checked and deployed to a local offline cache if missing.

> **Performance Recommendation:**
> * **For moderate data sizes (under 10–15 GB):** Runs smoothly and efficiently via **Termux on Android**.
> * **For large datasets:** Due to heavy video processing and rendering, running it on a **PC** is strongly recommended for optimal speed.

---

## 🚀 Quick Start

1. Ensure **Python 3.8+** is installed on your system.
2. Save the script as `Snapchat-memories-organizer-KBJ911.py` in your working directory.
3. Run the script:
   ```bash
   python Snapchat-memories-organizer-KBJ911.py
