

#!/usr/bin/env python3
import subprocess
import os
import sys

# --- 配置 ---
GITIGNORE_CONTENT = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtualenv
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs and editors
.vscode/
.idea/
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Other
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
logs/
*.log
*.bak
*.tmp
"""

def run_command(command_list, check=True, capture_output=False, text=True, shell=False, cwd=None):
    """辅助函数，用于执行系统命令并打印。"""
    print(f"🚀 Executing: {' '.join(command_list)}")
    try:
        result = subprocess.run(
            command_list,
            check=check,
            capture_output=capture_output,
            text=text,
            shell=shell,
            cwd=cwd
        )
        if capture_output:
            if result.stdout and result.stdout.strip():
                print(f"Stdout:\n{result.stdout.strip()}")
            if result.stderr and result.stderr.strip(): # 只有当stderr有内容时才打印
                print(f"Stderr:\n{result.stderr.strip()}", file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {' '.join(command_list)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if e.stdout and e.stdout.strip():
            print(f"Stdout:\n{e.stdout.strip()}", file=sys.stderr)
        if e.stderr and e.stderr.strip():
            print(f"Stderr:\n{e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: Command '{command_list[0]}' not found. Is Git installed and in your PATH?", file=sys.stderr)
        sys.exit(1)

def ask_yes_no(prompt, default_yes=True):
    """
    询问用户 Yes/No 问题。
    Enter 键默认为 'default_yes' 指定的值。
    返回 True 表示 Yes，False 表示 No。
    """
    if default_yes:
        indicator = "(Y/n)"
        default_answer = 'y'
    else:
        indicator = "(y/N)"
        default_answer = 'n'

    while True:
        answer = input(f"🤔 {prompt} {indicator}: ").strip().lower() or default_answer
        if answer in ['y', 'yes']:
            return True
        elif answer in ['n', 'no']:
            return False
        else:
            print("⚠️ Invalid input. Please enter 'y' or 'n'.")

def create_gitignore():
    """创建 .gitignore 文件并写入内容"""
    if os.path.exists(".gitignore"):
        print("ℹ️ .gitignore already exists. Skipping creation.")
        return
    try:
        with open(".gitignore", "w", encoding="utf-8") as f:
            f.write(GITIGNORE_CONTENT.strip() + "\n") # 添加一个换行符在末尾
        print("✅ .gitignore created successfully.")
    except IOError as e:
        print(f"❌ Error creating .gitignore: {e}", file=sys.stderr)
        # 不在此处退出，让主流程决定
        return False
    return True


def setup_new_project():
    """自动化新项目的初始设置流程"""
    print("\n--- 🌟 Setting up a New Project 🌟 ---")
    project_name_default = os.path.basename(os.getcwd())
    project_name = input(f"Enter project name for README.md (default: {project_name_default}): ").strip() or project_name_default

    github_user = input("Enter your GitHub username (e.g., buxuele): ").strip()
    if not github_user:
        print("❌ GitHub username cannot be empty.")
        return False # 返回False表示设置失败

    repo_name = input(f"Enter your GitHub repository name (e.g., {project_name}): ").strip() or project_name
    if not repo_name:
        print("❌ GitHub repository name cannot be empty.")
        return False
    
    remote_url = f"https://github.com/{github_user}/{repo_name}.git"
    print(f"ℹ️ Remote URL will be: {remote_url}")

    # 1. 创建 README.md
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"# {project_name}\n")
            print(f"✅ {readme_path} created.")
        except IOError as e:
            print(f"❌ Error creating {readme_path}: {e}", file=sys.stderr)
            return False
    else:
        print(f"ℹ️ {readme_path} already exists.")

    # 2. git init
    if os.path.exists(".git"):
        print("ℹ️ .git directory already exists. Assuming it's initialized.")
    else:
        run_command(["git", "init"])

    # 3. 创建 .gitignore
    if not create_gitignore(): # 如果创建失败
        if not ask_yes_no("Failed to create .gitignore. Continue without it?", default_yes=False):
            return False

    # 4. git add README.md and .gitignore (如果存在)
    files_to_add = [readme_path]
    if os.path.exists(".gitignore"):
        files_to_add.append(".gitignore")
    run_command(["git", "add"] + files_to_add)

    # 5. git commit
    run_command(["git", "commit", "-m", "first commit"])

    # 6. git branch -M main
    run_command(["git", "branch", "-M", "main"])

    # 7. git remote add or set-url origin
    remote_check_cmd = run_command(["git", "remote", "-v"], capture_output=True, check=False)
    current_origin_url = ""
    origin_found = False

    if remote_check_cmd.returncode == 0 and remote_check_cmd.stdout:
        for line in remote_check_cmd.stdout.strip().split('\n'):
            parts = line.split() # 分割一行，例如: origin  https://github.com/user/repo.git (fetch)
            if len(parts) >= 2 and parts[0] == "origin":
                origin_found = True
                # 通常第一个URL (fetch) 是我们关心的
                current_origin_url = parts[1]
                break 
    
    expected_ssh_url = f"git@github.com:{github_user}/{repo_name}.git"
    if origin_found:
        if current_origin_url == remote_url or current_origin_url == expected_ssh_url:
            print(f"ℹ️ Remote 'origin' already correctly set to: {current_origin_url}")
        else:
            print(f"⚠️ Existing 'origin' remote points to: {current_origin_url}")
            print(f"   New remote URL should be: {remote_url}")
            if ask_yes_no(f"Do you want to update 'origin' to '{remote_url}'?", default_yes=True):
                run_command(["git", "remote", "set-url", "origin", remote_url])
            else:
                print("ℹ️ Keeping existing 'origin' URL. Push might go to the wrong remote or fail.")
    else:
        print(f"ℹ️ Adding remote 'origin' with URL: {remote_url}")
        run_command(["git", "remote", "add", "origin", remote_url])

    # 8. git push -u origin main
    if ask_yes_no(f"Ready to push 'main' branch to '{remote_url}'?", default_yes=True):
        run_command(["git", "push", "-u", "origin", "main"])
        print("\n🎉 New project setup complete and pushed to GitHub!")
        run_command(["git", "status"])
    else:
        print("ℹ️ Push aborted by user. Setup is locally complete but not pushed.")
    return True


def push_changes():
    """自动化日常的 add, commit, push 流程"""
    print("\n--- 🚀 Pushing Changes 🚀 ---")
    if not os.path.exists(".git"):
        print("❌ Error: Not a git repository. Current directory is not under git control.", file=sys.stderr)
        print("💡 Try initializing a new project first if this is a new directory.", file=sys.stderr)
        return False

    # 确保分支是 main (或用户想要的分支，但这里强制为 main 以匹配 gg.bat)
    # 检查当前分支
    current_branch_cmd = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, check=False)
    if current_branch_cmd.returncode == 0:
        current_branch = current_branch_cmd.stdout.strip()
        if current_branch != "main":
            if ask_yes_no(f"Current branch is '{current_branch}'. Switch to 'main' and force its name (git branch -M main)?", default_yes=True):
                run_command(["git", "branch", "-M", "main"])
            else:
                print(f"ℹ️ Staying on branch '{current_branch}'. Pushing this branch instead of 'main'.")
                # 如果用户不想切换到main，后续命令应该使用 current_branch
                # 但为了简单和匹配原gg.bat，我们这里还是假设目标是main，如果用户拒绝，可能会出问题
                # 更安全的做法是，如果用户拒绝切换到main，则询问是否推送到 current_branch
                # 或者在此处提示并退出。目前，如果用户拒绝，后续的 push origin main 会尝试推main
                # 所以，我们最好在用户拒绝后，提示可能的问题。
                print(f"⚠️ Warning: Push command will still target 'origin main'. If you want to push '{current_branch}', please do it manually or modify the script.")
                # 或者更干脆：
                # print(f"ℹ️ Aborting push. Please checkout to 'main' or push '{current_branch}' manually.")
                # return False
        else:
             print("ℹ️ Already on 'main' branch or it was just set.")
             # 确保 main 是最新的命名方式，即使它已经是 main
             run_command(["git", "branch", "-M", "main"])

    else:
        print("⚠️ Could not determine current branch. Proceeding with 'git branch -M main'.")
        run_command(["git", "branch", "-M", "main"])


    print("\n--- Current Git Status ---")
    run_command(["git", "status"])
    print("--------------------------")

    commit_message = input("💬 Enter commit message: ").strip()
    if not commit_message:
        if not ask_yes_no("Commit message is empty. Proceed with push without committing new changes?", default_yes=False):
            print("ℹ️ Commit and push aborted.")
            return True # 操作被用户取消，但脚本本身没出错
        else: # 用户选择不提交，直接尝试推送
            print("Attempting to push existing commits...")
            run_command(["git", "push", "-u", "origin", "main"]) # -u for consistency
            print("\n--- Final Git Status ---")
            run_command(["git", "status"])
            print("✅ Push (of existing commits) attempted.")
            return True

    # git add .
    run_command(["git", "add", "."])

    # 检查是否有东西可提交 (在 add . 之后)
    status_result = run_command(["git", "status", "--porcelain"], capture_output=True, check=False)
    if status_result.returncode != 0:
        print("❌ Error getting git status after 'add'. Cannot proceed.", file=sys.stderr)
        return False
    
    if not status_result.stdout.strip():
        print("ℹ️ No changes staged for commit after 'git add .'. Working tree might have been clean or all files are gitignored.")
        if ask_yes_no("No changes to commit. Do you want to try pushing existing commits anyway?", default_yes=False):
            print("Attempting to push existing commits...")
            run_command(["git", "push", "-u", "origin", "main"]) # Use -u for consistency
            print("✅ Push (of existing commits) attempted.")
        else:
            print("ℹ️ Push aborted.")
        return True
    else:
        run_command(["git", "commit", "-m", commit_message])

    # git push -u origin main (与 gg.bat 行为一致)
    run_command(["git", "push", "-u", "origin", "main"])

    print("\n--- Final Git Status ---")
    run_command(["git", "status"])
    print("✅ Changes pushed successfully!")
    return True

def main():
    print("--- Git Automation Script ---")
    while True:
        print("\nWhat would you like to do?")
        print("  1. Setup a new project (init, add remote, first push)")
        print("  2. Push existing changes (add, commit, push)")
        print("  q. Quit")
        
        choice = input("Enter your choice (default: 2 for push): ").strip().lower() or "2"

        if choice == '1' or choice == 'new':
            if setup_new_project():
                print("\nNew project setup process finished.")
            else:
                print("\nNew project setup process encountered issues or was aborted.")
            break 
        elif choice == '2' or choice == 'push':
            if push_changes():
                print("\nPush process finished.")
            else:
                print("\nPush process encountered issues or was aborted.")
            break
        elif choice == 'q' or choice == 'quit':
            print("👋 Exiting script.")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or q.")
    
    print("\n--- Script Finished ---")

if __name__ == "__main__":
    main()