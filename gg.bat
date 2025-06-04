@echo off                 ; 关闭命令的回显，即执行命令时不会显示命令本身
:: 显示当前的 Git 状态
git status

git branch -M main

:: 提示用户输入提交信息
set /p message="Enter commit message: "

:: 将当前目录下的所有更改添加到 Git 的暂存区
git add .

:: 使用用户输入的提交信息来提交暂存区的更改
git commit -m "%message%"

:: 将本地的提交推送到远程仓库
git push -u origin main

:: 显示执行 git push 后的 Git 状态
git status