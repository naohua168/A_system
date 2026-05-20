"""Fix deploy_verify.py test output parsing"""
with open("f:/bs/A_system/scripts/deploy_verify.py", "r", encoding="utf-8") as f:
    content = f.read()

old = (
    '        summary_line = ""\n'
    '        for line in (raw_stdout + raw_stderr).split("\\n"):\n'
    '            if "passed" in line and ("failed" in line or "skipped" in line):\n'
    '                summary_line = line.strip()\n'
    '                break\n'
    '            # 也匹配 Java/Maven 测试报告\n'
    '            if "Tests run:" in line:\n'
    '                summary_line = line.strip()\n'
    '                break'
)

new = (
    '        summary_line = ""\n'
    '        # 从后往前找最后一条包含 passed/failed/skipped 数字的摘要行\n'
    '        for line in reversed((raw_stdout + raw_stderr).split("\\n")):\n'
    '            stripped = line.strip()\n'
    '            # pytest: "90 passed, 58 warnings in 108.86s"\n'
    '            if re.search(r"\\d+\\s+(passed|failed|skipped)", stripped):\n'
    '                summary_line = stripped\n'
    '                break\n'
    '            # Maven: "Tests run: 10, Failures: 0, Errors: 0"\n'
    '            if "Tests run:" in stripped:\n'
    '                summary_line = stripped\n'
    '                break\n'
    '            # Vitest: "Tests  8 passed (8)"\n'
    '            if re.search(r"Tests\\s+\\d+\\s+passed", stripped):\n'
    '                summary_line = stripped\n'
    '                break'
)

if old in content:
    content = content.replace(old, new)
    with open("f:/bs/A_system/scripts/deploy_verify.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("FIX APPLIED: test output parsing updated to reverse-search")
else:
    print("OLD TEXT NOT FOUND - checking if already updated...")
    if new in content:
        print("ALREADY FIXED")
    else:
        print("ERROR: Could not find the text to replace")
        # Debug: find where the text is
        idx = content.find("passed")
        if idx > 0:
            print(content[idx-200:idx+300])
