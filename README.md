# MongoDB Atlas Integration

To store scan results in MongoDB Atlas, set the following environment variables before running the scanner API:


```
MONGO_URI=mongodb+srv://harshitadutt267_db_user:Harshitadutt%4027@cluster-engine.o4cj0fm.mongodb.net/?appName=Cluster-engine
MONGODB_DB=scanner_results  # optional, default is 'scanner_results'
MONGODB_COLLECTION=scan_results  # optional, default is 'scan_results'
```

Example Docker run command:

```
docker run -e MONGO_URI="<your-mongodb-atlas-connection-string>" \
           -e MONGODB_DB="scanner_results" \
           -e MONGODB_COLLECTION="scan_results" \
           -p 8000:8000 scanner-api
```

After each scan, results will be inserted into the specified MongoDB collection.
# Multi-Language Security Scanner

A comprehensive static analysis tool that scans code for security vulnerabilities, code smells, and best-practice violations. The scanner supports multiple programming languages and provides detailed reports with remediation suggestions.

## Overview

This project contains multiple scanner implementations for different programming languages:

- **Python Scanner (v1 & v2)**: Static analysis for Python code
- **Terraform Scanner (v2)**: Security and configuration analysis for Terraform files

## Docker Deployment

### Building the Docker Image

```bash
docker build -t scanner-api .
```

### Running the Container

```bash
docker run -p 8000:8000 scanner-api
```

### Using Docker Compose (Optional)

```yaml
version: '3.8'
services:
  scanner-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## API Endpoints

- `POST /scan` - Scan a single file
- `POST /scan-folder` - Scan a zipped folder (for Terraform projects)
- `GET /health` - Health check endpoint

### Example Usage

```bash
# Scan a Python file
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@example.py"

# Scan a Terraform project (zipped)
curl -X POST "http://localhost:8000/scan-folder" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@terraform-project.zip"
```

Each scanner uses a generic rule engine that applies rules defined in JSON metadata files, making it easy to add new rules without modifying the core scanning logic.

## Project Structure

```
scanner/
├── python_v1/          # Python scanner (initial version)
├── python_v2/          # Python scanner (enhanced version)
├── terraform_v2/       # Terraform scanner
└── README.md          # This file
```

## Python Scanner (v2) - Recommended

The Python scanner analyzes Python source code using Abstract Syntax Tree (AST) analysis to detect:

- Security vulnerabilities (hardcoded secrets, weak cryptography, etc.)
- Code quality issues (complexity, naming conventions, etc.)
- Best practice violations (proper exception handling, type hints, etc.)
- Framework-specific issues (Django, Flask, AWS, etc.)

### Key Features

- **AST-based analysis**: Deep understanding of Python code structure
- **300+ rules**: Comprehensive rule set covering security, quality, and best practices
- **Generic rule engine**: Rules defined in JSON metadata for easy customization
- **Interactive scanning**: Choose specific test files to analyze
- **Detailed reports**: JSON output with line numbers, descriptions, and remediation advice

### Files

- `python_scanner.py`: Main scanner entry point
- `python_generic_rule.py`: Generic rule engine for Python AST
- `logic_implementations.py`: Custom logic implementations for complex rules
- `python_docs/`: Rule metadata (300+ JSON files)
- `test/`: Test Python files with various code patterns

### Usage

```bash
cd python_v2
python python_scanner.py
```

The scanner will:
1. Display available test files
2. Let you select a file to scan
3. Parse the file into an AST
4. Apply all applicable rules
5. Generate a detailed report

## Terraform Scanner (v2)

The Terraform scanner analyzes Terraform configuration files for:

- Security misconfigurations
- Resource access control issues
- Infrastructure best practices
- AWS-specific security patterns

### Key Features

- **Per-file and project-wide scanning**: Choose between independent file analysis or merged project analysis
- **Symbol resolution**: Understands variable references and data sources
- **Configuration validation**: Checks resource configurations against best practices
- **Security focus**: Emphasis on cloud security and access control

### Files

- `scanner_common.py`: Main entry point and shared utilities
- `scanner_file.py`: Per-file scanning logic
- `scanner_project.py`: Project-wide scanning with symbol resolution
- `generic_rule.py`: Generic rule engine for Terraform
- `terraform_docs1/`: Rule metadata JSON files
- `test/`: Test Terraform configurations

### Usage

```bash
cd terraform_v2
python scanner_common.py
```

## Rule System

Both scanners use a generic rule engine that separates rule logic from implementation:

### Rule Metadata Structure

```json
{
  "rule_id": "unique_rule_identifier",
  "title": "Human-readable rule title",
  "type": "CODE_SMELL|BUG|VULNERABILITY|SECURITY_HOTSPOT",
  "defaultSeverity": "Info|Minor|Major|Critical|Blocker",
  "description": "Detailed rule description",
  "message": "Issue message template",
  "tags": ["security", "performance", "maintainability"],
  "logic": {
    "condition": "Rule applicability logic",
    "patterns": "Detection patterns"
  },
  "examples": {
    "compliant": [...],
    "noncompliant": [...]
  }
}
```

### Adding New Rules

1. Create a new JSON metadata file in the appropriate `*_docs/` folder
2. Define the rule logic, patterns, and examples
3. The scanner will automatically load and apply the new rule

## Rule Categories

### Security Rules
- Hardcoded credentials detection
- Weak cryptography usage
- Input validation issues
- Access control misconfigurations
- Injection vulnerability patterns

### Code Quality Rules
- Complexity analysis
- Naming convention compliance
- Dead code detection
- Code duplication

### Best Practice Rules
- Framework-specific patterns
- Performance optimizations
- Maintainability improvements
- Testing best practices

## Output Format

Scanners generate JSON reports with the following structure:

```json
{
  "scan_info": {
    "file": "scanned_file.py",
    "timestamp": "2025-10-08T...",
    "rules_applied": 150
  },
  "findings": [
    {
      "rule_id": "rule_identifier",
      "title": "Issue title",
      "severity": "Major",
      "line": 42,
      "column": 10,
      "message": "Detailed issue description",
      "remediation": "How to fix this issue"
    }
  ]
}
```

## Requirements

### Python Dependencies
- Python 3.8+
- Standard library modules (ast, json, re, os, sys)
- No external dependencies required

### System Requirements
- Windows, macOS, or Linux
- Sufficient memory for AST processing of large files

## Development

### Running Tests

Each scanner includes test files in their respective `test/` directories:

```bash
# Python scanner tests
cd python_v2
python python_scanner.py
# Select test files interactively

# Terraform scanner tests
cd terraform_v2
python scanner_common.py
# Choose scan mode and test folder
```

### Extending the Scanner

1. **Add new rule metadata**: Create JSON files in the appropriate `*_docs/` folder
2. **Custom logic**: Add complex rule implementations in `logic_implementations.py`
3. **New language support**: Create new scanner directories following the established pattern

## Performance

- **Python Scanner**: Processes ~1000 lines/second
- **Terraform Scanner**: Handles projects with hundreds of files
- **Memory usage**: Scales with file size and complexity
- **Rule evaluation**: Optimized for fast pattern matching

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all existing tests pass
5. Submit a pull request

## License

This project is designed for educational and professional use in static code analysis and security scanning.

## Version History

- **v2**: Enhanced rule engines with improved AST analysis
- **v1**: Initial Python scanner implementation

## Support

For issues or questions:
1. Check the test files for usage examples
2. Review rule metadata for implementation details
3. Examine the scanner output for debugging information

---

*Last updated: October 8, 2025*