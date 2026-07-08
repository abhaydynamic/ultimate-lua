[app]
title = Lua Studio IDE
package.name = luastudioide
package.domain = org.abhay
source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,md,lua
version = 1.0

# Crucial dependencies mapping
requirements = python3==3.14.2,kivy==2.3.0,kivymd==1.2.0,pygments,lupa

orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.accept_sdk_license = True

# Native storage read/write permissions
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
