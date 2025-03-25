[app]
title = Colva APP
package.name = colvaapp
package.domain = org.colva
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,sqlite3  # Cambiado db por sqlite3
version = 1.0

requirements = python3,kivy,kivymd,pillow,reportlab

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE
android.arch = arm64-v8a

# iOS specific
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0

[buildozer]
log_level = 2
warn_on_root = 1
