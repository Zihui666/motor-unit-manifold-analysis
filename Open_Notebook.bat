@echo off
cd /d "%~dp0"
python -m jupyterlab "PCA90_Alignment_Controls.ipynb"
if errorlevel 1 pause
