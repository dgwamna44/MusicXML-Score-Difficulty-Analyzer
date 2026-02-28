Hi, welcome to the eXeMpLify repository! My name is Duroje Gwamna, and I am a composer and an IT professional by trade. 
I've always had an interest in writing for concert band, and have a couple published works through the Randall Standridge Music Company
Turns out there are several resources from varying publishers regarding the music grading system. Each one has its own guidelines, and it's up to the composer to use their best judgment when assigning that grade.

After working with my fellow colleagues who write for the concert band medium, I decided to develop a tool to help with the guesswork and offer some insights based on quantitative data.
Special shoutout especially to composer Matt Neufeld for his insight as fellow composer, and educator! Checkout his music at https://www.mattneufeldmusic.com/

Most composers work with a score writing software like Sibelius or Musescore, and have the capability of saving their music as a .musicXML file to share amongst people using different software.

Special shoutout to the folks from the Composer's Cove discord :)

Without further ado...


**What it does**

Given a MusicXML score, eXeMpLify:

1. **Parses** the score into a structured representation.
2. Runs a set of **feature analyzers** (each targets one musical dimension).
3. Produces:
   - an **observed grade** (overall)
   - per-analyzer **confidence / grade signals**
   - optional **measure-level “why” details** (flags, rule violations, outliers)

---


**Screenshots**
1. Click Load XML Score to get started (remember to export the score you want to analyze as a .musicXML file.
2. Once selected, the score will show up in the center. You can adjust the zoom as needed.
<img width="355" height="104" alt="image" src="https://github.com/user-attachments/assets/3b86ae9a-d889-4625-84d1-7f2e7de21d0d" />
<img width="688" height="662" alt="image" src="https://github.com/user-attachments/assets/5fdd78d2-8d8a-4257-aa5e-0444ce80c5dc" />


3. Select the grade you estimate the piece to be by selecting Options, and then the dropdown. You can choose to search through partial grades (like 2.5, 3.5), or if you want detailed analysis based on the grade you select only. 
<img width="312" height="463" alt="image" src="https://github.com/user-attachments/assets/208f0129-ded1-44b4-8796-b0f62919d6d9" />


4. Once finished, click OK, and each analyzer's confidence score, which is based on the selected grade, will populate on the left panel. Each icon over the bar will provide a detailed analysis that shows on the right panel.
<img width="506" height="485" alt="image" src="https://github.com/user-attachments/assets/e2d7fc0c-c82b-4c7e-b9b1-96da80bd7c0c" />

5. You'll get a scoring overview as long as there's more than one part analyzed (can't provide scoring analysis on solo music).
<img width="290" height="666" alt="image" src="https://github.com/user-attachments/assets/81427ad3-1ac0-40ac-93f3-3b56165c0178" />


6. A timeline with measure numbers, tempo, key, and meters will populate at the bottom. Clicking on a measure number will provide highlights that are found across all analyzers (uncommon rhythms, high C found in tuba part, etc)
<img width="1380" height="151" alt="image" src="https://github.com/user-attachments/assets/2ef6ac0f-5208-48e2-bb8f-24049b87641a" />


7. An estimated grade range will show on the bottom left (as long as Target Analysis Only is not selected). You can also choose to save the analysis as a csv/JSON.
<img width="270" height="683" alt="image" src="https://github.com/user-attachments/assets/0b048c39-9488-40cb-8a7e-3fe3bd386686" />


**Project structure**

High-level layout (main folders/scripts): 2

- `analyzers/` — individual analyzers + shared analyzer utilities
- `app_data/` — constants, canonical mappings, grade buckets, configuration
- `data/` — datasets / tables used by analyzers (publisher-derived or hand-curated)
- `data_processing/` — score parsing + transformation helpers
- `models/` — typed models used across analyzers
- `publisher_sources/` — ingestion/normalization for publisher-specific data
- `utilities/` — reusable helpers
- `html/` — front-end UI assets
- `flask_app.py` — web entrypoint 3
- `run_analysis.py` — CLI/runner entrypoint 4

`analyzers/__init__.py` exposes the analyzer base + at least the articulation confidence entrypoint. 

---


