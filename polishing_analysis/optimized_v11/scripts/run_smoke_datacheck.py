"""Gate V11-1: Submit keyword scope smoke datacheck using Abaqus CLI."""
import subprocess
import sys

work_dir = "D:/mcp/abaqus_mcp/abaqus_work"
job = "v11_scope_smoke"
inp = "v11_keyword_scope_smoke.inp"

cmd = f'cmd.exe /c "call abaqus job={job} input={inp} datacheck interactive"'

print(f"Running: {cmd}")
result = subprocess.run(cmd, shell=True, cwd=work_dir, capture_output=True, text=True, timeout=120)
print("STDOUT:")
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
print("STDERR:")
print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
print(f"Return code: {result.returncode}")
