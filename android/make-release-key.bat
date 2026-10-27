@echo off
rem ---------------------------------------------------------------------
rem Create the one signing key this app will use for the rest of its life.
rem
rem READ THIS FIRST. Android identifies an app by the key that signed it.
rem Every update must be signed with the SAME key, or a phone will refuse
rem to install it over the copy already there - the reader has to delete
rem the app and lose whatever is in it. There is no way to change the key
rem afterwards. So: run this ONCE, then back up BOTH files it leaves
rem behind, in two places, and never commit either of them.
rem
rem It writes:
rem   release.jks              the key itself
rem   keystore.properties      where the build finds it, and the passwords
rem Both are gitignored.
rem ---------------------------------------------------------------------
setlocal
set JAVA_HOME=C:\Android\jdk-17
set HERE=%~dp0

if exist "%HERE%release.jks" (
  echo.
  echo release.jks already exists. Not touching it.
  echo If you genuinely mean to start over, move it aside first - and
  echo understand that every copy of the app signed with the old key can
  echo then never be updated again.
  exit /b 1
)

if "%~1"=="" (
  echo Usage: make-release-key.bat "a long passphrase you will not lose"
  echo.
  echo Use something you can find again in five years. If you lose it the
  echo key is useless and the app can never be updated.
  exit /b 1
)

"%JAVA_HOME%\bin\keytool" -genkeypair -v ^
  -keystore "%HERE%release.jks" ^
  -alias codex ^
  -keyalg RSA -keysize 4096 ^
  -validity 10950 ^
  -storepass "%~1" -keypass "%~1" ^
  -dname "CN=The Jarrell Codex, OU=Jarrell Codex, O=Jarrell Codex, C=US"
if errorlevel 1 (
  echo keytool failed. Nothing was written.
  exit /b 1
)

> "%HERE%keystore.properties" echo storeFile=release.jks
>> "%HERE%keystore.properties" echo storePassword=%~1
>> "%HERE%keystore.properties" echo keyAlias=codex
>> "%HERE%keystore.properties" echo keyPassword=%~1

echo.
echo Done. Two files were written next to this script:
echo    release.jks            - the key. 30 years' validity, RSA 4096.
echo    keystore.properties    - where the build finds it, and the password.
echo.
echo BACK BOTH UP NOW, somewhere that is not this computer. Losing them
echo means no future version of this app can ever be installed over the
echo one people already have.
echo.
echo Then build a signed release with:
echo    gradle :app:assembleRelease
endlocal
