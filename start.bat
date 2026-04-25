@echo off
chcp 936 >nul
title AeroRegQA Launcher
color 0A
echo.
echo ========================================================
echo        AeroRegQA - Agentic RAG System
echo ========================================================
echo.

set "CP1=%USERPROFILE%\miniconda3\Scripts\activate.bat"
set "CP2=%USERPROFILE%\anaconda3\Scripts\activate.bat"
set "CP3=C:\ProgramData\miniconda3\Scripts\activate.bat"
set "CP4=C:\ProgramData\anaconda3\Scripts\activate.bat"

if exist "%CP1%" (call "%CP1%") else if exist "%CP2%" (call "%CP2%") else if exist "%CP3%" (call "%CP3%") else if exist "%CP4%" (call "%CP4%")

call conda activate academic-rag
if %errorlevel% neq 0 (
    echo [ERROR] conda activate failed
    pause
    exit /b
)

streamlit run ui/app.py --server.port 8501
pause