@echo off
cls
echo ========================================
echo   Job Radar System Starting...
echo ========================================

:: 1. Check Python Environment
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.9+ not found. Please install Python and add it to system PATH.
    pause
    exit /b
)

:: 2. Start Spider (Fetch Latest Jobs)
echo [1/3] Starting Spider...
start cmd /k "title JobRadar_Spider && python spider.py"

:: 3. Start AI Evaluator (Skip Old Companies)
timeout /t 5 >nul
echo [2/3] Starting AI Evaluator...
start cmd /k "title JobRadar_AI_Eval && python ai_scorer.py"

:: 4. Start Web Server (Streamlit)
:: 增加较长的等待时间，确保 streamlit 能够正常挂载端口
timeout /t 12 >nul
echo [3/3] Starting Web Server and Opening Browser...
:: 使用 /c 参数关闭窗口会在运行完后关闭，/k 保留窗口方便看日志
start cmd /k "title JobRadar_Web && streamlit run app.py --server.port 8501"

:: 给浏览器充足的时间等待 Streamlit 服务完全加载
timeout /t 8 >nul
start http://localhost:8501

echo.
echo ========================================
echo   ALL SYSTEMS STARTED SUCCESSFULLY!
echo   - Check the three pop-up black windows for progress
echo   - Your browser will auto-refresh in a moment
echo ========================================
pause