@echo off
Rem .bat startet das waerme web gui zur Prognose der Speicherstände
Rem Starte Anaconda prompt hier den Pfad zur .bat einfügen, der die anaconda prompt öffnet
call C:\Users\einkee\AppData\Local\miniconda3\Scripts\activate.bat
Rem activiere virtual environment mit nötigen python libraries
call conda activate warm
Rem change directory zu Ordner mit der main Python Datei waerme.py
call cd C:\Users\einkee\Documents\waerme
Rem benutzr streamlit run command um das web gui zu öffnen und befehle aus python Datei auszuführen
call streamlit run waerme.py
Rem cmd \k verhindert, dass sich Anaconda prompt und web gui von selbst schließen
cmd \k