from github import Github


def create_issue(github_token, repo_name, title, body):
    g = Github(github_token)
    repo = g.get_repo(repo_name)

    issue = repo.create_issue(
        title=title,
        body=body,
    )

    return issue.html_url