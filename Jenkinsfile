pipeline {
    agent any
    parameters {
        string(name: 'TARGET_REPO', defaultValue: '', description: 'Git URL of the repo to scan')
        string(name: 'TARGET_BRANCH', defaultValue: 'main', description: 'Branch to scan')
    }
    stages {
        stage('Clone Target Repo') {
            steps {
                sh 'rm -rf target_code'
                sh 'git clone -b $TARGET_BRANCH $TARGET_REPO target_code'
            }
        }
        stage('Run Security Scan') {
            steps {
                script {
                    // Verify scanner-api health
                    sh '''
                        # Wait for scanner-api to be healthy
                        echo "Verifying scanner-api health..."
                        until curl -s http://scanner-api:8000/health | grep -q '"status":"healthy"'; do
                            echo "Waiting for scanner API to be ready..."
                            sleep 2
                        done
                        echo "Scanner API is ready!"
                        
                        # Create a temporary directory for scan results
                        mkdir -p temp_results
                        
                        # Create zip of the entire codebase
                        cd target_code && zip -r ../project_code.zip .
                        cd ..
                        
                        # Run the multi-language security scan
                        echo "Starting security scan..."
                        curl -X POST "http://scanner-api:8000/scan-folder" \
                            -H "Content-Type: multipart/form-data" \
                            -F "zip_file=@project_code.zip" \
                            -o "temp_results/scan_results.json"
                            
                        echo "Scan completed successfully!"
                    '''
                }
            }
        }
        stage('Store Results') {
            steps {
                script {
                    def timestamp = new Date().format('yyyyMMdd_HHmmss')
                    def projectName = sh(script: "basename ${params.TARGET_REPO} .git", returnStdout: true).trim()
                    def resultsDir = "/home/harshita/scanner_results/${projectName}/${timestamp}"
                    
                    sh """
                        # Create results directory structure
                        mkdir -p ${resultsDir}
                        
                        # Store scan results with context
                        cp temp_results/scan_results.json ${resultsDir}/
                        
                        # Add scan metadata
                        echo '{
                            "scan_info": {
                                "repository": "${params.TARGET_REPO}",
                                "branch": "${params.TARGET_BRANCH}",
                                "timestamp": "${timestamp}",
                                "build_number": "${BUILD_NUMBER}"
                            }
                        }' > ${resultsDir}/scan_metadata.json
                        
                        # Store git commit info
                        cd target_code
                        git log -1 --format='{%n  "commit": "%H",%n  "author": "%an",%n  "date": "%ad",%n  "message": "%s"%n}' > ${resultsDir}/commit_info.json
                        cd ..
                        
                        # Cleanup temporary files
                        rm -rf temp_results project_code.zip target_code
                        
                        echo "Scan results stored in: ${resultsDir}"
                        echo "Results include: scan findings, metadata, and commit information"
                    """
                }
            }
        }
        
    }
    }
}
