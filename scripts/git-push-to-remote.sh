#!/bin/bash
# ============================================================
# 脚本名称: git-push-to-remote.sh
# 功能描述: 将当前本地 Git 项目自动推送至指定的远端仓库。
#           自动检测未提交更改、处理远端地址与分支、连接测试等。
# 使用方法: ./git-push-to-remote.sh [远端名称] [分支名称]
#           示例: ./git-push-to-remote.sh origin main
# ============================================================

set -e

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------- 检查 Git 环境 ----------
check_git_env() {
    if ! command -v git &>/dev/null; then
        log_error "未找到 git 命令，请先安装 Git。"
        exit 1
    fi

    if ! git rev-parse --git-dir &>/dev/null; then
        log_error "当前目录不是一个 Git 仓库。"
        exit 1
    fi
}

# ---------- 远端连接测试 ----------
test_remote_connectivity() {
    local remote_name="$1"
    local remote_url
    remote_url=$(git remote get-url "$remote_name" 2>/dev/null)

    log_info "正在测试远端连接: $remote_name -> $remote_url"

    # 使用 git ls-remote 测试连接（静默模式）
    if git ls-remote --quiet "$remote_name" &>/dev/null; then
        log_success "远端连接测试通过: $remote_name"
        return 0
    else
        log_error "远端连接测试失败！请检查网络或远端地址: $remote_name"
        log_error "远端 URL: $remote_url"
        return 1
    fi
}

# ---------- 提示并添加远端 ----------
add_remote_interactive() {
    local remote_name="$1"
    log_warn "本地不存在远端仓库 '$remote_name'。"

    while true; do
        read -r -p "请输入远端仓库 URL（例如 https://github.com/user/repo.git）: " remote_url
        if [[ -z "$remote_url" ]]; then
            log_error "URL 不能为空，请重新输入。"
            continue
        fi
        break
    done

    log_info "正在添加远端 '$remote_name' -> $remote_url"
    if git remote add "$remote_name" "$remote_url"; then
        log_success "远端添加成功: $remote_name"
    else
        log_error "添加远端失败。"
        exit 1
    fi
}

# ---------- 检查并创建本地分支 ----------
ensure_local_branch() {
    local branch="$1"
    if ! git show-ref --verify --quiet "refs/heads/$branch"; then
        log_warn "本地分支 '$branch' 不存在，正在创建..."
        git checkout -b "$branch"
        log_success "本地分支 '$branch' 创建并切换成功。"
    else
        git checkout "$branch" 2>/dev/null || true
        log_info "使用现有本地分支: $branch"
    fi
}

# ---------- 检查远端分支，若不存在则创建并建立追踪 ----------
ensure_remote_branch() {
    local remote_name="$1"
    local branch="$2"

    if git ls-remote --quiet --heads "$remote_name" "$branch" | grep -q "refs/heads/$branch"; then
        log_info "远端分支 '$remote_name/$branch' 已存在。"
    else
        log_warn "远端分支 '$remote_name/$branch' 不存在，将自动创建并推送。"
        # 首次推送时建立 upstream 追踪
        if git push -u "$remote_name" "$branch"; then
            log_success "远端分支 '$remote_name/$branch' 创建成功并建立追踪关系。"
            return 0
        else
            log_error "创建远端分支失败。"
            exit 1
        fi
    fi

    # 确保本地分支建立了 upstream 追踪关系
    local upstream
    upstream=$(git rev-parse --abbrev-ref "$branch"@{upstream} 2>/dev/null || true)
    if [[ -z "$upstream" ]]; then
        log_info "正在为本地分支 '$branch' 设置 upstream 追踪关系..."
        git branch -u "$remote_name/$branch" "$branch"
        log_success "追踪关系已建立: $branch -> $remote_name/$branch"
    fi
}

# ---------- 处理未提交更改 ----------
handle_uncommitted_changes() {
    # 检查是否有未暂存的更改或未提交的暂存
    if ! git diff --quiet --ignore-submodules HEAD 2>/dev/null; then
        local changed_files
        changed_files=$(git status --porcelain | wc -l)
        log_warn "检测到 $changed_files 个文件有未提交的更改。"

        log_info "正在暂存所有更改..."
        git add -A

        local commit_msg="auto-commit: $(date +'%Y-%m-%d %H:%M:%S')"
        log_info "正在自动提交: $commit_msg"
        if git commit -m "$commit_msg"; then
            log_success "自动提交成功。"
        else
            log_error "自动提交失败。"
            exit 1
        fi
    else
        log_info "工作区干净，无未提交更改。"
    fi
}

# ---------- 主流程 ----------
main() {
    echo ""
    echo "============================================="
    echo "        Git 自动推送脚本"
    echo "============================================="
    echo ""

    # 1. 检查 Git 环境
    check_git_env

    # 2. 解析参数
    REMOTE_NAME="${1:-origin}"
    BRANCH_NAME="${2:-$(git rev-parse --abbrev-ref HEAD)}"

    log_info "目标远端: $REMOTE_NAME"
    log_info "目标分支: $BRANCH_NAME"

    # 3. 确保本地分支存在
    ensure_local_branch "$BRANCH_NAME"

    # 4. 处理未提交更改
    handle_uncommitted_changes

    # 5. 检查远端是否存在，不存在则交互添加
    if ! git remote get-url "$REMOTE_NAME" &>/dev/null; then
        add_remote_interactive "$REMOTE_NAME"
    else
        local remote_url
        remote_url=$(git remote get-url "$REMOTE_NAME")
        log_info "远端 '$REMOTE_NAME' 已存在: $remote_url"
    fi

    # 6. 远端连接测试
    echo ""
    log_info "---------- 远端连接测试 ----------"
    if ! test_remote_connectivity "$REMOTE_NAME"; then
        log_error "远端连接测试未通过，中断推送操作。"
        log_error "请检查网络连接或远端仓库配置后重试。"
        exit 1
    fi
    echo ""

    # 7. 确保远端分支存在并建立追踪
    ensure_remote_branch "$REMOTE_NAME" "$BRANCH_NAME"

    # 8. 执行推送
    echo ""
    log_info "---------- 正在推送至远端 ----------"
    log_info "推送命令: git push $REMOTE_NAME $BRANCH_NAME"
    echo ""

    if git push "$REMOTE_NAME" "$BRANCH_NAME"; then
        echo ""
        log_success "========================================"
        log_success "推送成功！"
        log_success "分支: $BRANCH_NAME -> $REMOTE_NAME/$BRANCH_NAME"
        log_success "========================================"
    else
        echo ""
        log_error "========================================"
        log_error "推送失败！请检查以上错误信息。"
        log_error "可能的原因："
        log_error "  - 网络连接异常"
        log_error "  - 权限不足（SSH key / Token）"
        log_error "  - 远端仓库禁止推送"
        log_error "  - 本地分支落后于远端（需要先拉取）"
        log_error "========================================"
        exit 1
    fi
}

main "$@"
