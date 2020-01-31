elifePipeline {
    node('containers-jenkins-plugin') {
        def commit
        def jenkins_image_building_ci_pipeline = 'process/process-data-hub-airflow-image-update-repo-list'
        def git_url

        stage 'Checkout', {
            checkout scm
            commit = elifeGitRevision()
            git_url = getGitUrl()
        }

        stage 'Build and run tests', {
            withDataPipelineGcpCredentials {
                try {
                    sh "make build-dev"
                    sh "make ci-end2end-test"
                } finally {
                    sh "make ci-clean"
                }
            }
        }

        elifeMainlineOnly {
            stage 'Merge to master', {
                elifeGitMoveToBranch commit, 'master'
            }
            stage 'Build data pipeline image with latest commit', {
                triggerImageBuild(image_building_ci_pipeline, git_url, commit)
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

def triggerImageBuild(image_building_ci_pipeline, gitUrl, gitCommitRef){
    build job: image_building_ci_pipeline,  wait: false, parameters: [string(name: 'gitUrl', value: gitUrl), string(name: 'gitCommitRef', value: gitCommitRef)]
}

def getGitUrl() {
    return sh(script: "git config --get remote.origin.url", returnStdout: true).trim()
}


