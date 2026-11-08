@echo off
title GangaClothes - Sistema Completo (Parcial 2 SI2)
color 0A
echo ========================================================
echo       INICIANDO PLATAFORMA GANGACLOTHES SAAS
echo ========================================================
echo.
echo [1/2] Iniciando Servidor Backend (FastAPI en puerto 8001)...
start "GangaClothes Backend (FastAPI)" cmd /k "cd /d C:\Users\user\GangaClothes && set PYTHONPATH=C:\Users\user\GangaClothes\parcial2\backend&& parcial2\backend\.venv\Scripts\python -m uvicorn app.main:app --port 8001 --reload"

echo [2/2] Iniciando Servidor Frontend (Angular en puerto 4200)...
start "GangaClothes Frontend (Angular)" cmd /k "cd /d C:\Users\user\GangaClothes\parcial2\web && npx ng serve --port 4200"

echo.
echo Esperando que los servicios inicien...
timeout /t 6 >nul

echo Abriendo navegador en http://localhost:4200 ...
start http://localhost:4200

echo.
echo ========================================================
echo  SISTEMA EN EJECUCION
echo  - Frontend: http://localhost:4200
echo  - Backend:  http://127.0.0.1:8001 (Swagger: /docs)
echo  No cierres las ventanas de Backend y Frontend.
echo ========================================================
pause
