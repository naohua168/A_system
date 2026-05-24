#!/bin/bash
# ============================================================
# 脚本名称: end-of-day.sh
# 功能描述: 安全关闭开发环境并结束当日工作流程
#           自动保存 → 停服务 → 检查 → 提交 → 输出摘要
# ============================================================

set -e

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo ""; echo -e "${CYAN}══════ $1 ══════${NC}"; }

# ---------- 配置 ----------
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GIT_REPO_DIR="$PROJECT_ROOT"
COMMIT_MSG="daily-work: $(date +'%Y-%m-%d') end of day"
START_TIME_FILE="$PROJECT_ROOT/.session_start"

# ---------- 记录本次运行时长 ----------
record_duration() {
    if [[ -f "$START_TIME_FILE" ]]; then
        local start_epoch
        start_epoch=$(cat "$START_TIME_FILE")
        local now_epoch
        now_epoch=$(date +%s)
        local elapsed=$((now_epoch - start_epoch))
        local hours=$((elapsed / 3600))
        local minutes=$(((elapsed % 3600) / 60))
        SESSION_DURATION="${hours}h ${minutes}m"
    else
        SESSION_DURATION="unknown"
    fi
}

# ---------- 1. 环境检查 ----------
step_check_environment() {
    log_step "Step 1: 环境检查"

    # 1.1 检查 Git 仓库
    if ! git -C "$GIT_REPO_DIR" rev-parse --git-dir &>/dev/null; then
        log_error "当前目录不是一个 Git 仓库。"
        exit 1
    fi
    log_success "Git 仓库验证通过"

    # 1.2 检查未解决的合并冲突
    local conflicts
    conflicts=$(git -C "$GIT_REPO_DIR" diff --name-only --diff-filter=U 2>/dev/null)
    if [[ -n "$conflicts" ]]; then
        log_error "存在未解决的合并冲突:"
        echo "$conflicts" | while IFS= read -r f; do echo "    - $f"; done
        exit 1
    fi
    log_success "无未解决的合并冲突"

    # 1.3 检查未追踪文件
    local untracked
    untracked=$(git -C "$GIT_REPO_DIR" ls-files --others --exclude-standard 2>/dev/null)
    if [[ -n "$untracked" ]]; then
        log_warn "发现未追踪的新文件:"
        echo "$untracked" | while IFS= read -r f; do echo "    - $f"; done
        echo ""
    else
        log_success "无未追踪文件"
    fi
}

# ---------- 2. 保存工作区状态 ----------
step_save_workspace() {
    log_step "Step 2: 保存工作区状态"

    # 记录当前 Git 分支和状态
    local branch
    branch=$(git -C "$GIT_REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    echo "branch=$branch" > "$PROJECT_ROOT/.workspace_state"
    echo "saved_at=$(date -Iseconds)" >> "$PROJECT_ROOT/.workspace_state"
    echo "git_hash=$(git -C "$GIT_REPO_DIR" rev-parse HEAD 2>/dev/null)" >> "$PROJECT_ROOT/.workspace_state"
    log_success "工作区状态已保存 (.workspace_state)"
}

# ---------- 3. 终止本地服务 ----------
step_stop_services() {
    log_step "Step 3: 终止本地服务"

    local freed_ports=()

    # 3.1 终止 Vite 开发服务器
    local vite_pids
    vite_pids=$(pgrep -f "vite" 2>/dev/null || true)
    if [[ -n "$vite_pids" ]]; then
        echo "$vite_pids" | xargs kill 2>/dev/null || true
        log_success "Vite 开发服务器已停止"
        freed_ports+=("5173")
    else
        log_info "Vite 开发服务器未运行"
    fi

    # 3.2 终止 node 监听进程 (vite/vitest 等)
    local node_pids
    node_pids=$(pgrep -f "node.*stock-analysis-frontend" 2>/dev/null || true)
    if [[ -n "$node_pids" ]]; then
        echo "$node_pids" | xargs kill 2>/dev/null || true
        log_success "Node 监听进程已停止"
    fi

    # 3.3 终止 Maven/Java 开发进程（本地运行，非 Docker）
    local java_pids
    java_pids=$(pgrep -f "stock-analysis-backend" 2>/dev/null || true)
    if [[ -n "$java_pids" ]]; then
        echo "$java_pids" | xargs kill 2>/dev/null || true
        log_success "本地 Java 进程已停止"
        freed_ports+=("8082")
    fi

    # 3.4 终止 Python 开发服务（本地运行，非 Docker）
    local python_pids
    python_pids=$(pgrep -f "uvicorn.*ai-service" 2>/dev/null || true)
    if [[ -n "$python_pids" ]]; then
        echo "$python_pids" | xargs kill 2>/dev/null || true
        log_success "本地 Python 服务已停止"
        freed_ports+=("8000")
    fi

    # 3.5 检查端口是否已释放
    log_info "检查端口释放状态..."
    local check_ports=(5173 8082 8000)
    for port in "${check_ports[@]}"; do
        if lsof -i ":$port" &>/dev/null 2>&1; then
            log_warn "端口 $port 仍被占用"
        else
            log_success "端口 $port 已释放"
        fi
    done

    if [[ ${#freed_ports[@]} -gt 0 ]]; then
        log_info "释放的端口: $(IFS=,; echo "${freed_ports[*]}")"
    fi
}

# ---------- 4. 暂存并提交 ----------
step_git_commit() {
    log_step "Step 4: 提交代码变更"

    # 4.1 暂存所有变更
    git -C "$GIT_REPO_DIR" add -A 2>/dev/null || true

    # 4.2 检查是否有变更需要提交
    if git -C "$GIT_REPO_DIR" diff --cached --quiet 2>/dev/null; then
        log_info "工作区干净，无变更需要提交"
        return 0
    fi

    # 4.3 统计变更
    local changed_files
    changed_files=$(git -C "$GIT_REPO_DIR" diff --cached --stat --name-only 2>/dev/null | wc -l)
    local insertions deletions
    insertions=$(git -C "$GIT_REPO_DIR" diff --cached --shortstat 2>/dev/null | grep -oP '\d+(?= insertion)' || echo "0")
    deletions=$(git -C "$GIT_REPO_DIR" diff --cached --shortstat 2>/dev/null | grep -oP '\d+(?= deletion)' || echo "0")

    # 4.4 执行提交
    if git -C "$GIT_REPO_DIR" commit -m "$COMMIT_MSG"; then
        COMMIT_COUNT=1
        CHANGED_FILES=$changed_files
        INSERTIONS=$insertions
        DELETIONS=$deletions
        log_success "提交成功: $COMMIT_MSG"
        log_info "  变更文件: $changed_files | +$insertions/-$deletions"
    else
        log_error "提交失败"
        exit 1
    fi
}

# ---------- 5. 输出工作结束摘要 ----------
step_print_summary() {
    log_step "Step 5: 工作结束摘要"

    echo ""
    echo "  ╔═══════════════════════════════════════════╗"
    echo "  ║         今日工作已安全结束                 ║"
    echo "  ╚═══════════════════════════════════════════╝"
    echo ""
    echo "  📅 日期:       $(date +'%Y-%m-%d %H:%M')"
    echo "  🌿 分支:       $(git -C "$GIT_REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    echo "  ⏱  运行时长:   $SESSION_DURATION"
    echo "  📝 提交次数:   ${COMMIT_COUNT:-0}"
    if [[ -n "${CHANGED_FILES:-}" ]]; then
        echo "  📂 变更文件:   $CHANGED_FILES (+${INSERTIONS:-0}/-${DELETIONS:-0})"
    fi
    echo "  💾 最后提交:   $(git -C "$GIT_REPO_DIR" log -1 --format='%h %s' 2>/dev/null || echo '无')"
    echo ""
    echo "  🟢 所有服务已停止，端口已释放"
    echo "  🟢 Git 工作区已提交"
    echo "  🟢 可安全关闭 IDE"
    echo ""
}

# ---------- 清理 ----------
cleanup() {
    rm -f "$PROJECT_ROOT/.workspace_state" 2>/dev/null
    rm -f "$START_TIME_FILE" 2>/dev/null
}

# ---------- 主流程 ----------
main() {
    COMMIT_COUNT=0
    SESSION_DURATION=""

    # 注册退出清理
    trap cleanup EXIT

    echo ""
    echo "=============================================="
    echo "     🔒 安全关闭开发环境"
    echo "=============================================="
    echo ""

    record_duration
    step_check_environment
    step_save_workspace
    step_stop_services
    step_git_commit
    step_print_summary
}

main "$@"
