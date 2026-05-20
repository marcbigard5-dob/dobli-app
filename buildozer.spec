[app]

# (string) Title of your application
title = Dobli App

# (string) Package name
package.name = dobli

# (string) Package domain (needed for android packaging)
package.domain = com.marcbigard5

# (string) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (string) Application version
version = 0.1

# (list) Application requirements
requirements = python3==3.10.11,kivy==2.3.0

# (string) Supported orientations
orientation = portrait

# (fullscreen) Fullscreen setting
fullscreen = 0

# ==============================================================================
# Android specific configuration
# ==============================================================================

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 33

# (str) Android NDK version to use
android.ndk = 25c

# (int) Android NDK API to use
android.ndk_api = 21

# (bool) True if you accept the SDK license
android.accept_sdk_license = True

# (list) The Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup
android.allow_backup = True

# (list) Permissions
android.permissions = INTERNET

# (bool) Enable AndroidX support
android.enable_androidx = True

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug and up)
log_level = 2

# (int) Warn if buildozer is run as root
warn_on_root = 1
