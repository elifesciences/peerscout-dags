elifePipeline {
    node('containers-jenkins-plugin') {
        def image_repo = 'elifesciences/peerscout-dags'
        def jenkins_image_building_ci_pipeline = 'process/process-data-hub-airflow-image-update-repo-list'

        def commit
        def commitShort
        def branch
        def timestamp
        def git_url

        stage 'Checkout', {
            checkout scm
            commit = elifeGitRevision()
            commitShort = elifeGitRevision().substring(0, 8)
            branch = sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()
            timestamp = sh(script: 'date --utc +%Y%m%d.%H%M', returnStdout: true).trim()
            git_url = getGitUrl()
        }

        stage 'Build and run tests', {
            withDataPipelineGcpCredentials {
                try {
                    timeout(time: 30, unit: 'MINUTES') {
                        sh "make ci-build-dev"
                        sh "GOOGLE_APPLICATION_CREDENTIALS=./credentials.json \
                            make ci-test-including-end2end"
                    }
                } finally {
                    sh "docker-compose ps"
                    sh "docker-compose logs"
                    sh "make ci-clean"
                }
            }
        }

        stage 'Build main image', {
            sh "make IMAGE_REPO=${image_repo} IMAGE_TAG=${commit} ci-build-main-image"
        }

        elifeMainlineOnly {
            def dev_image_repo = image_repo + '_unstable'

            stage 'Merge to master', {
                elifeGitMoveToBranch commit, 'master'
            }

            stage 'Push image', {
                sh "make EXISTING_IMAGE_TAG=${commit} EXISTING_IMAGE_REPO=${image_repo} IMAGE_TAG=${commit} IMAGE_REPO=${dev_image_repo} retag-push-image"
                sh "make EXISTING_IMAGE_TAG=${commit} EXISTING_IMAGE_REPO=${image_repo} IMAGE_TAG=${branch}-${commitShort}-${timestamp} IMAGE_REPO=${dev_image_repo} retag-push-image"
                sh "make EXISTING_IMAGE_TAG=${commit} EXISTING_IMAGE_REPO=${image_repo} IMAGE_TAG=latest IMAGE_REPO=${dev_image_repo} retag-push-image"
            }

            stage 'Build data pipeline image with latest commit', {
                triggerImageBuild(jenkins_image_building_ci_pipeline, git_url, commit)
            }
        }

        elifeTagOnly { tagName ->
            def candidateVersion = tagName - "v"

            stage 'Push release image', {
                sh "make EXISTING_IMAGE_TAG=${commit} EXISTING_IMAGE_REPO=${image_repo} IMAGE_TAG=latest IMAGE_REPO=${image_repo} retag-push-image"
                sh "make EXISTING_IMAGE_TAG=${commit} EXISTING_IMAGE_REPO=${image_repo} IMAGE_TAG=${candidateVersion} IMAGE_REPO=${image_repo} retag-push-image"
            }
        }
    }
}

def withDataPipelineGcpCredentials(doSomething) {
    try {
        sh 'vault.sh kv get -field credentials secret/containers/data-pipeline/gcp > credentials.json'
        doSomething()
    } finally {
        sh 'echo > credentials.json'
    }
}

def triggerImageBuild(jenkins_image_building_ci_pipeline, gitUrl, gitCommitRef){
    build job: jenkins_image_building_ci_pipeline,  wait: false, parameters: [string(name: 'gitUrl', value: gitUrl), string(name: 'gitCommitRef', value: gitCommitRef)]
}

def getGitUrl() {
    return sh(script: "git config --get remote.origin.url", returnStdout: true).trim()
}
