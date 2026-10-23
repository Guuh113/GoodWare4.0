@echo off
setlocal
rem pushd supports local paths, spaces and network shares.
pushd "%~dp0"
if errorlevel 1 goto invalid_folder
rem Allow a launcher copied to the parent of the project folder.
if exist "requirements.txt" goto check_files
if exist "goodware-site1\requirements.txt" cd "goodware-site1"
:check_files
if not exist "requirements.txt" goto incomplete
if not exist "iniciar.py" goto incomplete
if not exist "app.py" goto incomplete
if not exist ".env.example" goto incomplete
set "GOODWARE_DIR=%CD%"
if exist "%GOODWARE_DIR%\.venv\Scripts\python.exe" goto install
where py >nul 2>&1
if errorlevel 1 goto python_fallback
py -3 -m venv "%GOODWARE_DIR%\.venv"
if errorlevel 1 goto environment_failed
goto install
:python_fallback
where python >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv "%GOODWARE_DIR%\.venv"
if errorlevel 1 goto environment_failed
:install
"%GOODWARE_DIR%\.venv\Scripts\python.exe" -m pip install -r "%GOODWARE_DIR%\requirements.txt"
if errorlevel 1 goto install_failed
"%GOODWARE_DIR%\.venv\Scripts\python.exe" "%GOODWARE_DIR%\iniciar.py"
if errorlevel 1 goto server_failed
popd
exit /b 0
:incomplete
echo.
echo A pasta do GoodWare esta incompleta.
echo O iniciador precisa estar junto de requirements.txt, iniciar.py, app.py e .env.example.
echo.
echo 1. Feche esta janela.
echo 2. Clique com o botao direito no ZIP e escolha Extrair Tudo.
echo 3. Abra a pasta EXTRAIDA e depois a pasta goodware-site1.
echo 4. Execute INICIAR_GOODWARE.bat nessa pasta.
echo.
echo Nao execute o BAT diretamente dentro do ZIP nem copie apenas o BAT.
goto fail
:invalid_folder
echo Nao foi possivel abrir a pasta do iniciador. Extraia o ZIP para uma pasta local.
pause
exit /b 1
:missing_python
echo Instale o Python 3.11 ou 3.12 e habilite Add Python to PATH.
goto fail
:environment_failed
echo Nao foi possivel criar o ambiente Python. Confira o erro acima e a permissao da pasta.
goto fail
:install_failed
echo Falha ao instalar dependencias. Confira o erro acima e sua conexao com a internet.
goto fail
:server_failed
echo O servidor nao iniciou. Confira o erro acima.
echo Se o erro informar porta ocupada, feche o servidor anterior ou altere PORT no .env.
:fail
pause
popd
exit /b 1
