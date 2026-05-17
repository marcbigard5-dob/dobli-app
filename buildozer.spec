[app]

title = Dobli App
package.name = dobli
package.domain = com.marcbigard5
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3==3.10.12,kivy==2.3.0
orientation = portrait
osx.kivy_version = 2.2.0
fullscreen = 0

# Android specific
android.api = 33
android.minapi = 24
android.sdk = 33
android.ndk = 25c
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
