[app]

title = Dobli
package.name = dobli
package.domain = org.dobli

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt

version = 0.1

requirements = python3==3.10.11,kivy==2.2.1,cython==0.29.36,pyjnius==1.6.1,plyer==2.1.0,requests==2.31.0,certifi==2024.2.2,setuptools==65.5.0,wheel==0.41.2

orientation = portrait

fullscreen = 0

android.api = 34
android.minapi = 21
android.sdk = 34
android.ndk = 25b
android.accept_sdk_license = True

p4a.branch = master

android.permissions = INTERNET

android.archs = arm64-v8a, armeabi-v7a

log_level = 2

warn_on_root = 1

# تحسينات الاستقرار
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core-ktx:1.10.1

# منع مشاكل build cache
build_dir = .buildozer

# تعطيل بعض الميزات المسببة للأعطال
android.copy_libs = 1

# أيقونة (اختياري)
# icon.filename = icon.png

# شاشة البداية (اختياري)
# presplash.filename = presplash.png
