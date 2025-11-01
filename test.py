# Example: Scan a Python file directly using your scanner logic

from python_v2.python_scanner import run_scan

file_path = "D:\\scanner\\python_v2\\test\\ast_to_dict_with_parent.py"  # Replace with your .py file path
results = run_scan(file_path)

print("Scan Results for Python file:")
for finding in results:
    print(finding)