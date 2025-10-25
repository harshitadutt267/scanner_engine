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
        stage('Detect Project Type') {
            steps {
                script {
                    def tfCount = sh(script: 'find target_code -name "*.tf" | wc -l', returnStdout: true).trim()
                    def pyCount = sh(script: 'find target_code -name "*.py" | wc -l', returnStdout: true).trim()
                    env.HAS_TF = (tfCount != '0')
                    env.HAS_PY = (pyCount != '0')
                }
            }
        }
        stage('Scan Terraform Project') {
            when {
                expression { env.HAS_TF == 'true' }
            }
            steps {
                sh 'cd target_code && zip -r ../target_code.zip .'
                                sh '''
                                curl -X POST "http://scanner-api:8000/scan-folder" \
                                    -F "zip_file=@target_code.zip" \
                                    -o scan_results.json
                                '''
            }
        }
        stage('Scan Python Files') {
            when {
                expression { env.HAS_PY == 'true' }
            }
            steps {
                sh '''
                for file in $(find target_code -name "*.py"); do
                    curl -X POST "http://scanner-api:8000/scan" -F "file=@$file" -o "scan_result_$(basename $file).json"
                done
                '''
            }
        }
        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: '*.json'
            }
        }
    }
}
