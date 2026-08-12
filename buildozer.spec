[app]
title = RX3 Texture Editor
package.name = rx3textureeditor
package.domain = org.rx3tools
source.dir = .
source.include_exts = py,png,jpg,kv,txt
version = 0.1
requirements = python3,kivy,pillow
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 35
android.minapi = 23
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
