[app]

# (string) Title of your application
title = Dobli

# (string) Package name
package.name = dobli

# (string) Package domain (needed for android packaging)
package.domain = org.dobli

# (string) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt

# (string) Application version
version = 0.1

# (list) Application requirements
requirements = python3==3.10.11,kivy==2.2.1,cython==0.29.36,pyjnius==1.6.1,ply==2.1.0,requests==2.31.0,certifi==2024.2.2,urllib3

# (string) Supported orientations
orientation = portrait

# (fullscreen) Fullscreen setting
fullscreen = 0

# ==============================================================================
# Android specific configuration
# ==============================================================================

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 34

# (str) Android NDK version to use
android.ndk = 25b

# (bool) True if you accept the SDK license
android.accept_sdk_license = True

# (str) python-for-android branch to use
p4a.branch = master

# (list) Permissions
android.permissions = INTERNET

# (list) The Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (int) Log level (0 = error only, 1 = info, 2 = debug and up)
log_level = 2

# (int) Warn if buildozer is run as root
warn_on_root = 1

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) Gradle dependencies
android.gradle_dependencies = androidx.core:core-ktx:1.10.1

# (str) Custom build directory
build_dir = .buildozer

# (int) Copy libraries instead of symlinking
android.copy_libs = 1
