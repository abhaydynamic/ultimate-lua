[app]
title = Lua Studio IDE
package.name = luastudioide
package.domain = org.abhay
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Crucial dependencies mapping
requirements = python3, kivy==2.3.0, kivymd==1.2.0, pygments, lupa

orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Native storage read/write permissions
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
